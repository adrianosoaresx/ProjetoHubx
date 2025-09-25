from __future__ import annotations

from django.conf import settings
from django.db import models

from core.models import SoftDeleteModel, TimeStampedModel


class AuditLog(TimeStampedModel, SoftDeleteModel):
    """Immutable audit log for user-facing actions."""

    class Status(models.TextChoices):
        SUCCESS = "SUCCESS", "Success"
        FAILURE = "FAILURE", "Failure"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="audit_logs",
    )
    action = models.CharField(max_length=100)
    object_type = models.CharField(max_length=100, blank=True)
    object_id = models.CharField(max_length=64, blank=True)
    ip_hash = models.CharField(max_length=64)
    status = models.CharField(max_length=10, choices=Status.choices)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        indexes = [models.Index(fields=["user", "created_at"])]
        ordering = ["-created_at"]
