from __future__ import annotations

from celery import shared_task
from django.utils import timezone

from .models import TokenUsoLog


@shared_task
def remover_logs_antigos() -> None:
    limite = timezone.now() - timezone.timedelta(days=365)
    TokenUsoLog.objects.filter(timestamp__lt=limite).delete()
