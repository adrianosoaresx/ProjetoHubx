from __future__ import annotations

import time

import sentry_sdk
import structlog
from asgiref.sync import async_to_sync
from celery import shared_task  # type: ignore
from channels.layers import get_channel_layer
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from audit.models import AuditLog
from audit.services import log_audit
from configuracoes.models import ConfiguracaoConta

from .models import Canal, HistoricoNotificacao, NotificationLog, NotificationStatus
from .services import metrics
from .services.email_client import send_email
from .services.push_client import send_push
from .services.whatsapp_client import send_whatsapp

logger = structlog.get_logger(__name__)
User = get_user_model()


@shared_task(bind=True, max_retries=3)
def enviar_notificacao_async(self, subject: str, body: str, log_id: str) -> None:
    start = time.perf_counter()
    log = NotificationLog.objects.get(id=log_id)
    user = log.user
    canal = log.canal
    template = log.template
    if log.status != NotificationStatus.PENDENTE:
        logger.info("log_invalido", log_id=str(log.id), status=log.status)
        return
    try:
        if canal == Canal.EMAIL:
            send_email(user, subject, body)
        elif canal == Canal.PUSH:
            send_push(user, body)
        elif canal == Canal.WHATSAPP:
            send_whatsapp(user, body)
        config = getattr(user, "configuracao", None)
        if config and config.receber_notificacoes_push and config.frequencia_notificacoes_push == "imediata":
            channel_layer = get_channel_layer()
            async_to_sync(channel_layer.group_send)(
                f"notificacoes_{user.id}",
                {
                    "type": "notification.message",
                    "event": "notification_message",
                    "titulo": subject,
                    "mensagem": body,
                    "canal": canal,
                    "timestamp": timezone.now().isoformat(),
                },
            )
        log.status = NotificationStatus.ENVIADA
        metrics.notificacoes_enviadas_total.labels(canal=canal).inc()
    except Exception as exc:  # pragma: no cover - integração externa
        log.status = NotificationStatus.FALHA
        log.erro = str(exc)
        metrics.notificacoes_falhas_total.labels(canal=canal).inc()
        log.data_envio = timezone.now()
        log.save(update_fields=["status", "erro", "data_envio"])
        with sentry_sdk.push_scope() as scope:
            scope.set_tag("module", "notificacoes")
            scope.set_context("notificacao", {"log_id": str(log.id), "canal": canal})
            sentry_sdk.capture_exception(exc)
        log_audit(
            user,
            "notification_send_failed",
            object_type="NotificationLog",
            object_id=str(log.id),
            status=AuditLog.Status.FAILURE,
            metadata={"canal": canal, "template": str(template.id)},
        )
        logger.exception(
            "falha_envio_notificacao",
            user_id=user.id,
            template=str(template.id),
            canal=canal,
        )
        raise self.retry(exc=exc, countdown=2**self.request.retries)
    else:
        log.data_envio = timezone.now()
        log.erro = None
        log.save(update_fields=["status", "data_envio", "erro"])
    finally:
        duration = time.perf_counter() - start
        metrics.notificacao_task_duration_seconds.labels(task="enviar_notificacao_async").observe(duration)
        logger.info(
            "notificacao_enviada",
            user_id=user.id,
            template=str(template.id),
            canal=canal,
            status=log.status,
            erro=log.erro,
            tipo_frequencia="imediata",
            duration=duration,
        )


def _enviar_resumo(config: ConfiguracaoConta, canais: list[str], agora, tipo: str) -> None:
    for canal in canais:
        start = time.perf_counter()
        logs = NotificationLog.objects.filter(user=config.user, canal=canal, status=NotificationStatus.PENDENTE)
        if not logs.exists():
            continue
        mensagens = [log.template.corpo for log in logs]
        body = "\n".join(mensagens)
        subject = _("Resumo de notificações")
        if canal == Canal.EMAIL:
            send_email(config.user, subject, body)
        elif canal == Canal.WHATSAPP:
            send_whatsapp(config.user, body)
        elif canal == Canal.PUSH:
            send_push(config.user, body)
        logs.update(status=NotificationStatus.ENVIADA, data_envio=agora)
        envio = agora.replace(second=0, microsecond=0)
        data_ref = agora.date()
        HistoricoNotificacao.objects.get_or_create(
            user=config.user,
            canal=canal,
            frequencia=tipo,
            data_referencia=data_ref,
            defaults={"conteudo": mensagens, "enviado_em": envio},
        )
        if config.receber_notificacoes_push and config.frequencia_notificacoes_push == tipo:
            channel_layer = get_channel_layer()
            async_to_sync(channel_layer.group_send)(
                f"notificacoes_{config.user.id}",
                {
                    "type": "notification.message",
                    "event": "notification_message",
                    "titulo": subject,
                    "mensagem": body,
                    "canal": canal,
                    "timestamp": envio.isoformat(),
                },
            )
        duration = time.perf_counter() - start
        metrics.notificacao_task_duration_seconds.labels(task=f"resumo_{tipo}").observe(duration)
        logger.info(
            "resumo_enviado",
            user_id=config.user.id,
            canal=canal,
            tipo_frequencia=tipo,
            duration=duration,
        )


@shared_task
def enviar_relatorios_diarios() -> None:
    agora = timezone.localtime()
    hora = agora.time().replace(second=0, microsecond=0)
    configs = ConfiguracaoConta.objects.select_related("user").filter(hora_notificacao_diaria=hora)
    for config in configs:
        canais: list[str] = []
        if config.receber_notificacoes_email and config.frequencia_notificacoes_email == "diaria":
            canais.append(Canal.EMAIL)
        if config.receber_notificacoes_whatsapp and config.frequencia_notificacoes_whatsapp == "diaria":
            canais.append(Canal.WHATSAPP)
        if config.receber_notificacoes_push and config.frequencia_notificacoes_push == "diaria":
            canais.append(Canal.PUSH)
        _enviar_resumo(config, canais, agora, "diaria")


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
        if config.receber_notificacoes_email and config.frequencia_notificacoes_email == "semanal":
            canais.append(Canal.EMAIL)
        if config.receber_notificacoes_whatsapp and config.frequencia_notificacoes_whatsapp == "semanal":
            canais.append(Canal.WHATSAPP)
        if config.receber_notificacoes_push and config.frequencia_notificacoes_push == "semanal":
            canais.append(Canal.PUSH)
        _enviar_resumo(config, canais, agora, "semanal")
