from __future__ import annotations

import uuid
from decimal import Decimal

from django.conf import settings
from django.db import models
from django.utils import timezone

from core.fields import EncryptedCharField, URLField
from core.models import SoftDeleteModel, TimeStampedModel

"""Modelos do módulo financeiro."""


class CentroCusto(TimeStampedModel, SoftDeleteModel):
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


class ContaAssociado(TimeStampedModel, SoftDeleteModel):
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


class LancamentoFinanceiro(TimeStampedModel, SoftDeleteModel):
    """Registro financeiro com data de vencimento para controle de inadimplência."""

    class Tipo(models.TextChoices):
        MENSALIDADE_ASSOCIACAO = "mensalidade_associacao", "Mensalidade Associação"
        MENSALIDADE_NUCLEO = "mensalidade_nucleo", "Mensalidade Núcleo"
        INGRESSO_EVENTO = "ingresso_evento", "Ingresso Evento"
        APORTE_INTERNO = "aporte_interno", "Aporte Interno"
        APORTE_EXTERNO = "aporte_externo", "Aporte Externo"
        DESPESA = "despesa", "Despesa"
        AJUSTE = "ajuste", "Ajuste"

    class Status(models.TextChoices):
        PENDENTE = "pendente", "Pendente"
        PAGO = "pago", "Pago"
        CANCELADO = "cancelado", "Cancelado"

    class Origem(models.TextChoices):
        MANUAL = "manual", "Manual"
        IMPORTACAO = "importacao", "Importação"

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
    origem = models.CharField(max_length=20, choices=Origem.choices, default=Origem.MANUAL)
    descricao = models.TextField(blank=True)
    ultima_notificacao = models.DateTimeField(null=True, blank=True)
    lancamento_original = models.ForeignKey(
        "self", on_delete=models.SET_NULL, null=True, blank=True, related_name="ajustes"
    )
    ajustado = models.BooleanField(default=False)

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
            models.Index(
                fields=["centro_custo", "conta_associado", "tipo", "valor", "data_lancamento"],
                name="idx_lanc_duplicidade",
            ),
            models.Index(
                fields=["centro_custo", "conta_associado", "status", "data_vencimento"],
                name="idx_lanc_cc_status_venc",
            ),
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


class ImportacaoPagamentos(TimeStampedModel, SoftDeleteModel):
    """Registro de importações de pagamentos em massa."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    arquivo = models.CharField(max_length=255)
    data_importacao = models.DateTimeField(default=timezone.now)
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    total_processado = models.PositiveIntegerField(default=0)
    erros = models.JSONField(default=list, blank=True)
    class Status(models.TextChoices):
        PROCESSANDO = "processando", "Em processamento"
        CONCLUIDO = "concluido", "Concluído"
        ERRO = "erro", "Erro"

    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PROCESSANDO)

    class Meta:
        ordering = ["-data_importacao"]
        verbose_name = "Importação de Pagamentos"
        verbose_name_plural = "Importações de Pagamentos"
        indexes = [models.Index(fields=["data_importacao"], name="idx_importacao_data")]

    def __str__(self) -> str:
        return f"{self.arquivo} ({self.total_processado})"


class FinanceiroLog(TimeStampedModel, SoftDeleteModel):
    """Registros de auditoria das ações financeiras."""

    class Acao(models.TextChoices):
        IMPORTAR = "importar", "Importar Pagamentos"
        CRIAR_COBRANCA = "criar_cobranca", "Criar Cobrança"
        DISTRIBUIR_RECEITA = "distribuir_receita", "Distribuir Receita"
        AJUSTE_LANCAMENTO = "ajuste_lancamento", "Ajuste de Lançamento"
        REPASSE = "repasse", "Repasse de Receita"
        EDITAR_CENTRO = "editar_centro", "Editar Centro de Custo"
        EDITAR_LANCAMENTO = "editar_lancamento", "Editar Lançamento"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
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


class FinanceiroTaskLog(TimeStampedModel, SoftDeleteModel):
    """Armazena o resultado das tarefas assíncronas do módulo financeiro."""

    nome_tarefa = models.CharField(max_length=255)
    executada_em = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20)
    detalhes = models.TextField(blank=True)

    class Meta:
        ordering = ["-executada_em"]
        verbose_name = "Log de Tarefa Financeira"
        verbose_name_plural = "Logs de Tarefas Financeiras"
        indexes = [models.Index(fields=["nome_tarefa", "executada_em"], name="idx_task_nome_exec")]

    def __str__(self) -> str:
        return f"{self.nome_tarefa} - {self.status}"


class IntegracaoConfig(TimeStampedModel, SoftDeleteModel):
    """Configurações de provedores externos."""

    class Tipo(models.TextChoices):
        ERP = "erp", "ERP"
        CONTABILIDADE = "contabilidade", "Contabilidade"
        GATEWAY = "gateway", "Gateway de Pagamento"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    nome = models.CharField(max_length=255)
    tipo = models.CharField(max_length=20, choices=Tipo.choices)
    base_url = URLField(max_length=255)
    credenciais_encrypted = EncryptedCharField(max_length=512, blank=True)

    class Meta:
        ordering = ["nome"]
        verbose_name = "Configuração de Integração"
        verbose_name_plural = "Configurações de Integração"

    def __str__(self) -> str:  # pragma: no cover - simples representação
        return self.nome


class IntegracaoIdempotency(TimeStampedModel):
    """Armazena chaves de idempotência utilizadas nas integrações."""

    idempotency_key = models.CharField(max_length=255, unique=True)
    provedor = models.CharField(max_length=100)
    recurso = models.CharField(max_length=100)
    status = models.CharField(max_length=50)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Idempotência de Integração"
        verbose_name_plural = "Idempotências de Integração"


class IntegracaoLog(TimeStampedModel):
    """Registra as chamadas realizadas aos provedores externos."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    provedor = models.CharField(max_length=100)
    acao = models.CharField(max_length=100)
    payload_in = models.JSONField(default=dict, blank=True)
    payload_out = models.JSONField(default=dict, blank=True)
    status = models.CharField(max_length=50)
    duracao_ms = models.PositiveIntegerField(default=0)
    erro = models.TextField(blank=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Log de Integração"
        verbose_name_plural = "Logs de Integração"

    def __str__(self) -> str:  # pragma: no cover - simples representação
        return f"{self.provedor} - {self.acao}"
