from __future__ import annotations

import uuid

from django.contrib.auth import get_user_model
from django.db import models
from django.utils import timezone

from core.models import SoftDeleteModel, TimeStampedModel

User = get_user_model()


class WebhookSubscription(TimeStampedModel, SoftDeleteModel):
    """Representa uma inscrição de webhook para um usuário."""

    id: models.UUIDField = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user: models.ForeignKey = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="webhook_subscriptions"
    )
    url: models.URLField = models.URLField()
    secret: models.CharField = models.CharField(max_length=255)
    active: models.BooleanField = models.BooleanField(default=True)
    revoked_at: models.DateTimeField = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def revoke(self) -> None:
        """Revoga a inscrição do webhook."""
        if self.active:
            self.active = False
            self.revoked_at = timezone.now()
            self.save(update_fields=["active", "revoked_at"])


class WebhookEvent(TimeStampedModel):
    """Evento pendente de envio para um webhook."""

    id: models.UUIDField = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    subscription: models.ForeignKey = models.ForeignKey(
        WebhookSubscription, on_delete=models.CASCADE, related_name="events"
    )
    event: models.CharField = models.CharField(max_length=100)
    payload: models.JSONField = models.JSONField()
    delivered: models.BooleanField = models.BooleanField(default=False)
    attempts: models.PositiveIntegerField = models.PositiveIntegerField(default=0)
    last_attempt_at: models.DateTimeField = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
