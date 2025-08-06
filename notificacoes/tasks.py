from __future__ import annotations

import logging

import sentry_sdk
from celery import shared_task  # type: ignore
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from configuracoes.models import ConfiguracaoConta

from .models import Canal, HistoricoNotificacao, NotificationLog, NotificationStatus
from .services import metrics
from .services.email_client import send_email
from .services.push_client import send_push
from .services.whatsapp_client import send_whatsapp

logger = logging.getLogger(__name__)
User = get_user_model()


@shared_task(bind=True, max_retries=3)
def enviar_notificacao_async(self, subject: str, body: str, log_id: str) -> None:
    log = NotificationLog.objects.get(id=log_id)
    user = log.user
    canal = log.canal
    template = log.template
    if log.status != NotificationStatus.PENDENTE:
        logger.info(
            "Log em estado inválido", extra={"log_id": str(log.id), "status": log.status}
        )
        return
    try:
        if canal == Canal.EMAIL:
            send_email(user, subject, body)
        elif canal == Canal.PUSH:
            send_push(user, body)
        elif canal == Canal.WHATSAPP:
            send_whatsapp(user, body)
        log.status = NotificationStatus.ENVIADA
        metrics.notificacoes_enviadas_total.labels(canal=canal).inc()
    except Exception as exc:  # pragma: no cover - integração externa
        log.status = NotificationStatus.FALHA
        log.erro = str(exc)
        metrics.notificacoes_falhadas_total.labels(canal=canal).inc()
        log.data_envio = timezone.now()
        log.save(update_fields=["status", "erro", "data_envio"])
        sentry_sdk.capture_exception(exc)
        logger.exception(
            "Falha no envio de notificação",
            extra={"user": user.id, "template": str(template.id), "canal": canal},
        )
        raise self.retry(exc=exc, countdown=2 ** self.request.retries)
    else:
        log.data_envio = timezone.now()
        log.erro = None
        log.save(update_fields=["status", "data_envio", "erro"])
    finally:
        logger.info(
            "notificacao_enviada",
            extra={
                "user": user.id,
                "template": str(template.id),
                "canal": canal,
                "status": log.status,
                "erro": log.erro,
            },
        )


def _enviar_resumo(config: ConfiguracaoConta, canais: list[str], agora) -> None:
    for canal in canais:
        logs = NotificationLog.objects.filter(
            user=config.user, canal=canal, status=NotificationStatus.PENDENTE
        )
        if not logs.exists():
            continue
        mensagens = [log.template.corpo for log in logs]
        body = "\n".join(mensagens)
        subject = _("Resumo de notificações")
        if canal == Canal.EMAIL:
            send_email(config.user, subject, body)
        elif canal == Canal.WHATSAPP:
            send_whatsapp(config.user, body)
        logs.update(status=NotificationStatus.ENVIADA, data_envio=agora)
        envio = agora.replace(second=0, microsecond=0)
        HistoricoNotificacao.objects.get_or_create(
            user=config.user,
            canal=canal,
            enviado_em=envio,
            defaults={"conteudo": mensagens},
        )


@shared_task
def enviar_relatorios_diarios() -> None:
    agora = timezone.localtime()
    hora = agora.time().replace(second=0, microsecond=0)
    configs = ConfiguracaoConta.objects.select_related("user").filter(
        hora_notificacao_diaria=hora
    )
    for config in configs:
        canais: list[str] = []
        if (
            config.receber_notificacoes_email
            and config.frequencia_notificacoes_email == "diaria"
        ):
            canais.append(Canal.EMAIL)
        if (
            config.receber_notificacoes_whatsapp
            and config.frequencia_notificacoes_whatsapp == "diaria"
        ):
            canais.append(Canal.WHATSAPP)
        _enviar_resumo(config, canais, agora)


@shared_task
def enviar_relatorios_semanais() -> None:
    agora = timezone.localtime()
    hora = agora.time().replace(second=0, microsecond=0)
    weekday = agora.weekday()
    configs = ConfiguracaoConta.objects.select_related("user").filter(
        dia_semana_notificacao=weekday, hora_notificacao_semanal=hora
    )
    for config in configs:
        canais: list[str] = []
        if (
            config.receber_notificacoes_email
            and config.frequencia_notificacoes_email == "semanal"
        ):
            canais.append(Canal.EMAIL)
        if (
            config.receber_notificacoes_whatsapp
            and config.frequencia_notificacoes_whatsapp == "semanal"
        ):
            canais.append(Canal.WHATSAPP)
        _enviar_resumo(config, canais, agora)
