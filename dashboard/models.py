from __future__ import annotations

import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django_extensions.db.models import TimeStampedModel

from accounts.models import UserType
from core.models import SoftDeleteModel, SoftDeleteManager


class DashboardFilter(SoftDeleteModel, TimeStampedModel):
    objects = SoftDeleteManager()
    all_objects = models.Manager()

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    nome = models.CharField(max_length=100)
    filtros = models.JSONField()
    publico = models.BooleanField(default=False)

    def __str__(self) -> str:  # pragma: no cover - simple representation
        return self.nome

    def clean(self):
        if self.publico and self.user_id and self.user.user_type not in {UserType.ROOT, UserType.ADMIN}:
            raise ValidationError({"publico": "Somente admins podem tornar público"})


class DashboardConfig(SoftDeleteModel, TimeStampedModel):
    objects = SoftDeleteManager()
    all_objects = models.Manager()

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    nome = models.CharField(max_length=100)
    config = models.JSONField()
    publico = models.BooleanField(default=False)

    class Meta:
        get_latest_by = "modified"

    def clean(self):
        if self.publico and self.user_id and self.user.user_type not in {UserType.ROOT, UserType.ADMIN}:
            raise ValidationError({"publico": "Somente admins podem tornar público"})

    def __str__(self) -> str:  # pragma: no cover - simples
        return self.nome


class Achievement(TimeStampedModel):
    """Representa uma conquista disponível para os usuários."""

    code = models.CharField(max_length=50, unique=True)
    titulo = models.CharField(max_length=100)
    descricao = models.TextField()
    criterio = models.CharField(max_length=200)
    icon = models.CharField(max_length=200, blank=True)

    def __str__(self) -> str:  # pragma: no cover - simples representação
        return self.titulo


class UserAchievement(TimeStampedModel):
    """Conquistas obtidas por um usuário."""

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    achievement = models.ForeignKey(Achievement, on_delete=models.CASCADE)
    completado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("user", "achievement")

    def __str__(self) -> str:  # pragma: no cover - simples representação
        return f"{self.user} - {self.achievement}"
