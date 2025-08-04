"""Core mixins shared across applications."""

from django.db import models
from django.utils import timezone
from django.utils.timezone import now


class TimeStampedModel(models.Model):
    """Abstract base class with self-updating ``created_at`` and ``updated_at`` fields."""

    created_at: models.DateTimeField = models.DateTimeField(default=now, editable=False)
    updated_at: models.DateTimeField = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class SoftDeleteModel(models.Model):
    """Mixin that implements logical deletion via ``deleted`` and ``deleted_at``."""

    deleted: models.BooleanField = models.BooleanField(default=False)
    deleted_at: models.DateTimeField = models.DateTimeField(null=True, blank=True)

    class Meta:
        abstract = True

    def delete(self, using: str | None = None, keep_parents: bool = False, soft: bool = True) -> None:
        if soft:
            self.deleted = True
            self.deleted_at = timezone.now()
            self.save(update_fields=["deleted", "deleted_at"])
            return
        super().delete(using=using, keep_parents=keep_parents)

    def soft_delete(self) -> None:
        """Atalho para executar a exclusão lógica."""
        self.delete()

    def hard_delete(self, using: str | None = None, keep_parents: bool = False) -> None:
        """Remove definitivamente o registro."""
        super().delete(using=using, keep_parents=keep_parents)


class SoftDeleteManager(models.Manager):
    """Manager que retorna apenas objetos não deletados logicamente."""

    def get_queryset(self) -> models.QuerySet:  # type: ignore[override]
        return super().get_queryset().filter(deleted=False)
