from __future__ import annotations

import uuid
from decimal import Decimal

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
    organizacao = models.UUIDField(null=True, blank=True)
    nucleo = models.UUIDField(null=True, blank=True)
    evento = models.UUIDField(null=True, blank=True)
    saldo = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0"))

    class Meta:
        ordering = ["nome"]
        verbose_name = "Centro de Custo"
        verbose_name_plural = "Centros de Custo"

    def __str__(self) -> str:
        return self.nome


class ContaAssociado(TimeStampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user_id = models.UUIDField()
    saldo = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0"))

    class Meta:
        ordering = ["user_id"]
        verbose_name = "Conta do Associado"
        verbose_name_plural = "Contas dos Associados"

    def __str__(self) -> str:
        return str(self.user_id)


class LancamentoFinanceiro(TimeStampedModel):
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
    tipo = models.CharField(max_length=32, choices=Tipo.choices)
    valor = models.DecimalField(max_digits=12, decimal_places=2)
    data_lancamento = models.DateTimeField(default=timezone.now)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDENTE)
    descricao = models.TextField(blank=True)

    class Meta:
        ordering = ["-data_lancamento"]
        verbose_name = "Lançamento Financeiro"
        verbose_name_plural = "Lançamentos Financeiros"

    def __str__(self) -> str:
        return f"{self.get_tipo_display()} - {self.valor}"


class Aporte(LancamentoFinanceiro):
    class Meta:
        proxy = True
        verbose_name = "Aporte"
        verbose_name_plural = "Aportes"

    def save(self, *args, **kwargs):
        if self.tipo not in {self.Tipo.APORTE_INTERNO, self.Tipo.APORTE_EXTERNO}:
            self.tipo = self.Tipo.APORTE_INTERNO
        super().save(*args, **kwargs)
