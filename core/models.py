from django.db import models
from django.utils.timezone import now


class TimeStampedModel(models.Model):
    """Abstract base class with self-updating ``created_at`` and ``updated_at``."""

    created_at = models.DateTimeField(default=now, editable=False)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True
