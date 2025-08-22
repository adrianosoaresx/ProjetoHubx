from __future__ import annotations

from celery import shared_task
from django.utils import timezone

from .models import ApiToken, ApiTokenLog, TokenUsoLog


@shared_task
def remover_logs_antigos() -> None:
    limite = timezone.now() - timezone.timedelta(days=365)
    TokenUsoLog.all_objects.filter(created_at__lt=limite).delete()
    ApiTokenLog.all_objects.filter(created_at__lt=limite).delete()


@shared_task
def revogar_tokens_expirados() -> None:
    now = timezone.now()
    tokens = ApiToken.objects.filter(expires_at__lt=now, revoked_at__isnull=True)
    for token in tokens:
        token.revoked_at = now
        token.revogado_por = token.user  # automatic revocation by owner, if any
        token.deleted = True
        token.deleted_at = now
        token.save(
            update_fields=["revoked_at", "revogado_por", "deleted", "deleted_at"]
        )
        ApiTokenLog.objects.create(
            token=token,
            usuario=None,
            acao=ApiTokenLog.Acao.REVOGACAO,
            ip=None,
        )
