from __future__ import annotations

import uuid
from decimal import Decimal

from django.conf import settings
from django.db import models
from django.utils import timezone

from core.models import TimeStampedModel


class CentroCusto(TimeStampedModel):
    class Tipo(models.TextChoices):
        ORGANIZACAO = "organizacao", "Organização"
        NUCLEO = "nucleo", "Núcleo"
        EVENTO = "evento", "Evento"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    nome = models.CharField(max_length=255)
    tipo = models.CharField(max_length=12, choices=Tipo.choices)
    organizacao = models.ForeignKey(
        "organizacoes.Organizacao",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="centros_custo",
    )
    nucleo = models.ForeignKey(
        "nucleos.Nucleo",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="centros_custo",
    )
    evento = models.ForeignKey(
        "agenda.Evento",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="centros_custo",
    )
    saldo = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0"))

    class Meta:
        ordering = ["nome"]
        verbose_name = "Centro de Custo"
        verbose_name_plural = "Centros de Custo"

    def __str__(self) -> str:
        return self.nome


class ContaAssociado(TimeStampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="contas_financeiras",
        db_column="user_id",
    )
    saldo = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0"))

    class Meta:
        ordering = ["user"]
        verbose_name = "Conta do Associado"
        verbose_name_plural = "Contas dos Associados"

    def __str__(self) -> str:
        return f"{self.user.email} (saldo: {self.saldo})"


class LancamentoFinanceiro(TimeStampedModel):
    """Registro financeiro com data de vencimento para controle de inadimplência."""

    class Tipo(models.TextChoices):
        MENSALIDADE_ASSOCIACAO = "mensalidade_associacao", "Mensalidade Associação"
        MENSALIDADE_NUCLEO = "mensalidade_nucleo", "Mensalidade Núcleo"
        INGRESSO_EVENTO = "ingresso_evento", "Ingresso Evento"
        APORTE_INTERNO = "aporte_interno", "Aporte Interno"
        APORTE_EXTERNO = "aporte_externo", "Aporte Externo"

    class Status(models.TextChoices):
        PENDENTE = "pendente", "Pendente"
        PAGO = "pago", "Pago"
        CANCELADO = "cancelado", "Cancelado"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    centro_custo = models.ForeignKey(CentroCusto, on_delete=models.CASCADE, related_name="lancamentos")
    conta_associado = models.ForeignKey(
        ContaAssociado, on_delete=models.CASCADE, null=True, blank=True, related_name="lancamentos"
    )
    originador = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="aportes_lancados",
    )
    tipo = models.CharField(max_length=32, choices=Tipo.choices)
    valor = models.DecimalField(max_digits=12, decimal_places=2)
    data_lancamento = models.DateTimeField(default=timezone.now)
    data_vencimento = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Data limite para pagamento do lançamento",
    )
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDENTE)
    descricao = models.TextField(blank=True)

    class Meta:
        ordering = ["-data_lancamento"]
        verbose_name = "Lançamento Financeiro"
        verbose_name_plural = "Lançamentos Financeiros"
        indexes = [models.Index(fields=["centro_custo", "conta_associado"], name="idx_centro_conta")]

    def __str__(self) -> str:
        return f"{self.get_tipo_display()} - {self.valor}"

    def save(self, *args, **kwargs) -> None:
        if not self.data_vencimento:
            self.data_vencimento = self.data_lancamento
        super().save(*args, **kwargs)


class Aporte(LancamentoFinanceiro):
    class Meta:
        proxy = True
        verbose_name = "Aporte"
        verbose_name_plural = "Aportes"

    def save(self, *args, **kwargs):
        if self.tipo not in {self.Tipo.APORTE_INTERNO, self.Tipo.APORTE_EXTERNO}:
            self.tipo = self.Tipo.APORTE_INTERNO
        super().save(*args, **kwargs)
