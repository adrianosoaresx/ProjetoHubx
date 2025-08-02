from __future__ import annotations

import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from accounts.models import UserType
from core.models import TimeStampedModel


class DashboardFilter(TimeStampedModel):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    nome = models.CharField(max_length=100)
    filtros = models.JSONField()

    def __str__(self) -> str:  # pragma: no cover - simple representation
        return self.nome


class DashboardConfig(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    nome = models.CharField(max_length=100)
    config = models.JSONField()
    publico = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def clean(self):
        if (
            self.publico
            and self.user_id
            and self.user.user_type not in {UserType.ROOT, UserType.ADMIN}
        ):
            raise ValidationError({"publico": "Somente admins podem tornar público"})

    def __str__(self) -> str:  # pragma: no cover - simples
        return self.nome
