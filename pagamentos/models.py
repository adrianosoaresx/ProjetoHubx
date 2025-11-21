from __future__ import annotations

from decimal import Decimal

from django.db import models
from django.utils.translation import gettext_lazy as _


class Pedido(models.Model):
    class Status(models.TextChoices):
        PENDENTE = "pending", _("Pendente")
        PAGO = "paid", _("Pago")
        CANCELADO = "cancelled", _("Cancelado")

    valor: Decimal = models.DecimalField(verbose_name=_("Valor"), max_digits=12, decimal_places=2)
    status: str = models.CharField(
        verbose_name=_("Status"),
        max_length=20,
        choices=Status.choices,
        default=Status.PENDENTE,
    )
    external_id: str | None = models.CharField(
        verbose_name=_("Identificador externo"),
        max_length=100,
        blank=True,
        null=True,
    )
    criado_em = models.DateTimeField(verbose_name=_("Criado em"), auto_now_add=True)
    atualizado_em = models.DateTimeField(verbose_name=_("Atualizado em"), auto_now=True)

    class Meta:
        verbose_name = _("Pedido")
        verbose_name_plural = _("Pedidos")
        ordering = ("-criado_em",)

    def __str__(self) -> str:
        return f"{self._meta.verbose_name} #{self.pk}"


class Transacao(models.Model):
    class Status(models.TextChoices):
        PENDENTE = "pending", _("Pendente")
        APROVADA = "approved", _("Aprovada")
        ESTORNADA = "refunded", _("Estornada")
        FALHOU = "failed", _("Falhou")

    pedido: Pedido = models.ForeignKey(
        Pedido,
        verbose_name=_("Pedido"),
        related_name="transacoes",
        on_delete=models.CASCADE,
    )
    valor: Decimal = models.DecimalField(verbose_name=_("Valor"), max_digits=12, decimal_places=2)
    status: str = models.CharField(
        verbose_name=_("Status"),
        max_length=20,
        choices=Status.choices,
        default=Status.PENDENTE,
    )
    external_id: str | None = models.CharField(
        verbose_name=_("Identificador externo"),
        max_length=100,
        blank=True,
        null=True,
    )
    criado_em = models.DateTimeField(verbose_name=_("Criado em"), auto_now_add=True)
    atualizado_em = models.DateTimeField(verbose_name=_("Atualizado em"), auto_now=True)

    class Meta:
        verbose_name = _("Transação")
        verbose_name_plural = _("Transações")
        ordering = ("-criado_em",)

    def __str__(self) -> str:
        return f"{self._meta.verbose_name} #{self.pk}"
