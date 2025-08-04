from __future__ import annotations

import uuid
from decimal import Decimal

from django.conf import settings
from django.db import models
from django.utils import timezone

from core.models import TimeStampedModel

"""Modelos do módulo financeiro."""


class CentroCusto(TimeStampedModel):
    """Centro de custos para organizar movimentações financeiras."""

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
    """Conta corrente vinculada a um usuário associado."""

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
    ultima_notificacao = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-data_lancamento"]
        verbose_name = "Lançamento Financeiro"
        verbose_name_plural = "Lançamentos Financeiros"
        indexes = [
            models.Index(fields=["centro_custo", "conta_associado"], name="idx_centro_conta"),
            models.Index(fields=["centro_custo"], name="idx_lanc_centro"),
            models.Index(fields=["conta_associado"], name="idx_lanc_conta"),
            models.Index(fields=["data_lancamento"], name="idx_lanc_dt_lanc"),
            models.Index(fields=["data_vencimento"], name="idx_lanc_dt_venc"),
            models.Index(fields=["status"], name="idx_lanc_status"),
        ]

    def __str__(self) -> str:
        return f"{self.get_tipo_display()} - {self.valor}"

    def save(self, *args, **kwargs) -> None:
        """Define vencimento padrão e persiste o lançamento."""
        if not self.data_vencimento:
            self.data_vencimento = self.data_lancamento
        super().save(*args, **kwargs)


class Aporte(LancamentoFinanceiro):
    """Proxy de ``LancamentoFinanceiro`` para representar aportes."""

    class Meta:
        proxy = True
        verbose_name = "Aporte"
        verbose_name_plural = "Aportes"

    def save(self, *args, **kwargs):
        """Garante tipo válido e salva o aporte."""
        if self.tipo not in {self.Tipo.APORTE_INTERNO, self.Tipo.APORTE_EXTERNO}:
            self.tipo = self.Tipo.APORTE_INTERNO
        super().save(*args, **kwargs)


class ImportacaoPagamentos(TimeStampedModel):
    """Registro de importações de pagamentos em massa."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    arquivo = models.CharField(max_length=255)
    data_importacao = models.DateTimeField(default=timezone.now)
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    total_processado = models.PositiveIntegerField(default=0)
    erros = models.JSONField(default=list, blank=True)

    class Meta:
        ordering = ["-data_importacao"]
        verbose_name = "Importação de Pagamentos"
        verbose_name_plural = "Importações de Pagamentos"

    def __str__(self) -> str:
        return f"{self.arquivo} ({self.total_processado})"


class FinanceiroLog(TimeStampedModel):
    """Registros de auditoria das ações financeiras."""

    class Acao(models.TextChoices):
        IMPORTAR = "importar", "Importar Pagamentos"
        GERAR_COBRANCA = "gerar_cobranca", "Gerar Cobrança"
        REPASSE = "repasse", "Repasse de Receita"
        EDITAR_CENTRO = "editar_centro", "Editar Centro de Custo"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True
    )
    acao = models.CharField(max_length=20, choices=Acao.choices)
    dados_anteriores = models.JSONField(default=dict, blank=True)
    dados_novos = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Log Financeiro"
        verbose_name_plural = "Logs Financeiros"

    def __str__(self) -> str:
        usuario = self.usuario.email if self.usuario else "desconhecido"
        return f"{self.get_acao_display()} - {usuario}"


class FinanceiroTaskLog(models.Model):
    """Armazena o resultado das tarefas assíncronas do módulo financeiro."""

    nome_tarefa = models.CharField(max_length=255)
    executada_em = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20)
    detalhes = models.TextField(blank=True)

    class Meta:
        ordering = ["-executada_em"]
        verbose_name = "Log de Tarefa Financeira"
        verbose_name_plural = "Logs de Tarefas Financeiras"

    def __str__(self) -> str:
        return f"{self.nome_tarefa} - {self.status}"
