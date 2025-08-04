from __future__ import annotations

from celery import shared_task
from django.conf import settings
from django.utils import timezone

from notificacoes.services.notificacoes import enviar_para_usuario

from .models import AccountToken, User


@shared_task
def send_password_reset_email(token_id: int) -> None:
    token = AccountToken.objects.select_related("usuario").get(pk=token_id)
    if token.used_at or token.expires_at < timezone.now():
        return
    url = f"{settings.FRONTEND_URL}/reset-password/?token={token.codigo}"
    enviar_para_usuario(
        token.usuario,
        "password_reset",
        {"url": url, "nome": token.usuario.first_name},
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
        {"url": url, "nome": token.usuario.first_name},
    )


@shared_task
def purge_soft_deleted() -> None:
    limit = timezone.now() - timezone.timedelta(days=30)
    qs = User.objects.filter(deleted=True, deleted_at__lt=limit, exclusao_confirmada=True)
    for user in qs:
        user.delete(soft=False)
