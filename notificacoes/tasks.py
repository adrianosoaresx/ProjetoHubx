from __future__ import annotations

import logging

import sentry_sdk
from celery import shared_task  # type: ignore
from django.contrib.auth import get_user_model
from django.utils import timezone

from .models import Canal, NotificationLog, NotificationStatus
from .services import metrics
from .services.notifications_client import send_email, send_push, send_whatsapp

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
