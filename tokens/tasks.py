from __future__ import annotations

from celery import shared_task
from django.utils import timezone

from .models import ApiToken, TokenUsoLog


@shared_task
def remover_logs_antigos() -> None:
    limite = timezone.now() - timezone.timedelta(days=365)
    TokenUsoLog.objects.filter(created_at__lt=limite).delete()


@shared_task
def revogar_tokens_expirados() -> None:
    now = timezone.now()
    ApiToken.objects.filter(expires_at__lt=now, revoked_at__isnull=True).update(revoked_at=now)
