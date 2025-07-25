from __future__ import annotations

from django.conf import settings
from django.db import models

from core.models import TimeStampedModel


class DashboardFilter(TimeStampedModel):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    nome = models.CharField(max_length=100)
    filtros = models.JSONField()

    def __str__(self) -> str:  # pragma: no cover - simple representation
        return self.nome
