from __future__ import annotations

import logging

from celery import shared_task  # type: ignore
from django.contrib.auth import get_user_model
from django.utils import timezone

from .models import NotificationLog, NotificationStatus, NotificationTemplate
from .services import metrics
from .services.notifications_client import send_email, send_push, send_whatsapp

logger = logging.getLogger(__name__)
User = get_user_model()


@shared_task(bind=True, max_retries=3, autoretry_for=(Exception,))
def enviar_notificacao_async(
    self, user_id: int, template_id: int, canal: str, subject: str, body: str, log_id: int
) -> None:
    user = User.objects.get(id=user_id)
    NotificationTemplate.objects.get(id=template_id)  # ensure exists
    log = NotificationLog.objects.get(id=log_id)
    try:
        if canal == "email":
            send_email(user, subject, body)
        elif canal == "push":
            send_push(user, body)
        elif canal == "whatsapp":
            send_whatsapp(user, body)
        log.status = NotificationStatus.ENVIADA
    except Exception as exc:  # pragma: no cover - integração externa
        log.status = NotificationStatus.FALHA
        log.erro = str(exc)
        logger.exception("Falha no envio de notificação")
        raise
    finally:
        log.data_envio = timezone.now()
        log.save(update_fields=["status", "erro", "data_envio"])
        metrics.notificacoes_enviadas_total.inc()
