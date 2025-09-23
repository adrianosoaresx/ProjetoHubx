from __future__ import annotations

import uuid
from decimal import Decimal

from django.db import models
from django.utils.translation import gettext_lazy as _

from core.models import SoftDeleteModel, TimeStampedModel


class Carteira(TimeStampedModel, SoftDeleteModel):
    """Carteira financeira vinculada a um centro de custo ou conta associado."""

    class Tipo(models.TextChoices):
        OPERACIONAL = "operacional", _("Operacional")
        RESERVA = "reserva", _("Reserva")
        INVESTIMENTO = "investimento", _("Investimento")

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    centro_custo = models.ForeignKey(
        "financeiro.CentroCusto",
        on_delete=models.CASCADE,
        related_name="carteiras",
        null=True,
        blank=True,
    )
    conta_associado = models.ForeignKey(
        "financeiro.ContaAssociado",
        on_delete=models.CASCADE,
        related_name="carteiras",
        null=True,
        blank=True,
    )
    nome = models.CharField(max_length=255)
    tipo = models.CharField(max_length=20, choices=Tipo.choices)
    descricao = models.TextField(blank=True)
    saldo = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0"))

    class Meta:
        ordering = ["nome"]
        verbose_name = "Carteira"
        verbose_name_plural = "Carteiras"
        constraints = [
            models.UniqueConstraint(
                fields=["centro_custo", "tipo"],
                name="uniq_carteira_centro_tipo",
            ),
            models.UniqueConstraint(
                fields=["conta_associado", "tipo"],
                name="uniq_carteira_conta_tipo",
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(centro_custo__isnull=False, conta_associado__isnull=True)
                    | models.Q(centro_custo__isnull=True, conta_associado__isnull=False)
                ),
                name="carteira_single_owner",
            ),
        ]
        indexes = [
            models.Index(fields=["centro_custo"], name="idx_carteira_centro"),
            models.Index(fields=["tipo"], name="idx_carteira_tipo"),
            models.Index(fields=["conta_associado"], name="idx_carteira_conta"),
        ]

    def __str__(self) -> str:
        return f"{self.nome} ({self.get_tipo_display()})"
