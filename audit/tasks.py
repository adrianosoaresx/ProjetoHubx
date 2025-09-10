from __future__ import annotations

from datetime import timedelta

from celery import shared_task
from django.conf import settings
from django.utils import timezone
from sentry_sdk import capture_exception

from .models import AuditLog


@shared_task
def cleanup_old_logs() -> int:
    """Soft delete logs older than retention period."""
    try:
        cutoff = timezone.now() - timedelta(days=365 * settings.AUDIT_LOG_RETENTION_YEARS)
        qs = AuditLog.objects.filter(created_at__lt=cutoff, deleted=False)
        count = qs.update(deleted=True, deleted_at=timezone.now())
        return count
    except Exception as exc:  # pragma: no cover - segurança
        capture_exception(exc)
        return 0
