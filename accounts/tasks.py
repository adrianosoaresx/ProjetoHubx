from __future__ import annotations

import logging

from celery import shared_task
from django.conf import settings
from django.db import transaction
from django.utils import timezone

from notificacoes.services.notificacoes import enviar_para_usuario

from .models import AccountToken, User

logger = logging.getLogger(__name__)


@shared_task
def send_password_reset_email(token_id: int) -> None:
    token = AccountToken.objects.select_related("usuario").get(pk=token_id)
    if token.used_at or token.expires_at < timezone.now():
        return
    url = f"{settings.FRONTEND_URL}/reset-password/?token={token.codigo}"
    enviar_para_usuario(
        token.usuario,
        "password_reset",
        {"url": url, "nome": token.usuario.contato},
    )


@shared_task
def send_confirmation_email(token_id: int) -> None:
    token = AccountToken.objects.select_related("usuario").get(pk=token_id)
    if token.used_at or token.expires_at < timezone.now():
        return
    url = f"{settings.FRONTEND_URL}/confirm-email/?token={token.codigo}"
    enviar_para_usuario(
        token.usuario,
        "email_confirmation",
        {"url": url, "nome": token.usuario.contato},
    )


@shared_task
def send_cancel_delete_email(token_id: int) -> None:
    token = AccountToken.objects.select_related("usuario").get(pk=token_id)
    if token.used_at or token.expires_at < timezone.now():
        return
    url = f"{settings.FRONTEND_URL}/cancel-delete/?token={token.codigo}"
    enviar_para_usuario(
        token.usuario,
        "cancel_delete",
        {"url": url, "nome": token.usuario.contato},
    )


@shared_task
def purge_soft_deleted(batch_size: int = 500) -> None:
    """Remove definitivamente usuários marcados como excluídos há mais de 30 dias."""
    limit = timezone.now() - timezone.timedelta(days=30)
    total_purged = 0
    try:
        while True:
            ids: list[int] = list(
                User.all_objects.filter(
                    deleted=True,
                    deleted_at__lte=limit,
                )
                .order_by("pk")
                .values_list("pk", flat=True)[:batch_size]
            )
            if not ids:
                break
            with transaction.atomic():
                # ``soft=False`` remove definitivamente
                for user in User.all_objects.filter(pk__in=ids).prefetch_related("medias"):
                    for media in user.medias.all():
                        media.delete(soft=False)
                    user.delete(soft=False)
            total_purged += len(ids)
    except Exception:
        logger.exception("accounts.purge_soft_deleted.error")
        raise
    if total_purged:
        logger.info("accounts.purge_soft_deleted", extra={"count": total_purged})
    else:
        logger.warning("accounts.purge_soft_deleted.noop")
