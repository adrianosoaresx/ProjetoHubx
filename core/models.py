from django.db import models
from django.utils import timezone
from django.utils.timezone import now


class TimeStampedModel(models.Model):
    """Abstract base class with self-updating ``created_at`` and ``updated_at``."""

    created_at: models.DateTimeField = models.DateTimeField(default=now, editable=False)
    updated_at: models.DateTimeField = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class SoftDeleteModel(models.Model):
    """Mixin que implementa exclusão lógica via ``deleted_at``."""

    deleted_at: models.DateTimeField = models.DateTimeField(null=True, blank=True)

    class Meta:
        abstract = True

    def delete(
        self, using: str | None = None, keep_parents: bool = False, soft: bool = True
    ) -> None:
        if soft:
            self.deleted_at = timezone.now()
            self.save(update_fields=["deleted_at"])
            return
        super().delete(using=using, keep_parents=keep_parents)
