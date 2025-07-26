from __future__ import annotations

from celery import shared_task
from django.conf import settings
from django.core.mail import send_mail
from django.utils import timezone

from .models import AccountToken, User


@shared_task
def send_password_reset_email(token_id: int) -> None:
    token = AccountToken.objects.select_related("usuario").get(pk=token_id)
    if token.used_at or token.expires_at < timezone.now():
        return
    url = f"{settings.FRONTEND_URL}/reset-password/?token={token.codigo}"
    send_mail(
        "Redefina sua senha",
        f"Acesse o link para redefinir sua senha: {url}",
        settings.DEFAULT_FROM_EMAIL,
        [token.usuario.email],
    )


@shared_task
def send_confirmation_email(token_id: int) -> None:
    token = AccountToken.objects.select_related("usuario").get(pk=token_id)
    if token.used_at or token.expires_at < timezone.now():
        return
    url = f"{settings.FRONTEND_URL}/confirm-email/?token={token.codigo}"
    send_mail(
        "Confirme seu email",
        f"Clique no link para confirmar: {url}",
        settings.DEFAULT_FROM_EMAIL,
        [token.usuario.email],
    )


@shared_task
def purge_soft_deleted() -> None:
    limit = timezone.now() - timezone.timedelta(days=30)
    qs = User.objects.filter(deleted_at__lt=limit, exclusao_confirmada=True)
    qs.delete()
