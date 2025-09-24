from __future__ import annotations

import uuid
from decimal import Decimal

from django.conf import settings
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from core.models import SoftDeleteModel, TimeStampedModel

from .carteira import Carteira

"""Modelos do módulo financeiro."""


class CentroCusto(TimeStampedModel, SoftDeleteModel):
    """Centro de custos para organizar movimentações financeiras."""

    _saldo_total_carteiras_cache: Decimal | None = None

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
        "eventos.Evento",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="centros_custo",
    )
    descricao = models.TextField(blank=True)

    class Meta:
        ordering = ["nome"]
        verbose_name = "Centro de Custo"
        verbose_name_plural = "Centros de Custo"

    def __str__(self) -> str:
        return self.nome

    @property
    def saldo_total_carteiras(self) -> Decimal:
        """Soma os saldos das carteiras ativas vinculadas ao centro."""

        if self._saldo_total_carteiras_cache is not None:
            return self._saldo_total_carteiras_cache
        total = (
            self.carteiras.filter(deleted=False)
            .aggregate(total=models.Sum("saldo"))
            .get("total")
        )
        total_decimal = total if total is not None else Decimal("0")
        self._saldo_total_carteiras_cache = total_decimal
        return total_decimal

    @saldo_total_carteiras.setter
    def saldo_total_carteiras(self, value: Decimal | None) -> None:
        """Permite que anotações de queryset preencham o cache."""

        if value is None:
            self._saldo_total_carteiras_cache = Decimal("0")
        elif isinstance(value, Decimal):
            self._saldo_total_carteiras_cache = value
        else:
            self._saldo_total_carteiras_cache = Decimal(value)


class ContaAssociado(TimeStampedModel, SoftDeleteModel):
    """Modelo legado mantido apenas para compatibilidade com lançamentos antigos.

    Utilize :class:`financeiro.models.Carteira` vinculada a associados para novas
    integrações. O campo ``conta_associado`` permanece disponível apenas para
    leitura e migração de dados existentes.
    """

    LEGACY_MESSAGE = _(
        "ContaAssociado é um modelo legado; utilize carteiras vinculadas ao associado"
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="contas_financeiras",
        db_column="user_id",
    )
    saldo = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0"))

    class Meta:
        managed = False
        ordering = ["user"]
        verbose_name = "Conta do Associado"
        verbose_name_plural = "Contas dos Associados"

    def __str__(self) -> str:
        return f"{self.user.email} (saldo: {self.saldo})"

    def save(self, *args, **kwargs) -> None:  # type: ignore[override]
        """Impede alterações em ambiente de desenvolvimento."""

        legacy_override = kwargs.pop("legacy_override", False)
        if settings.DEBUG and not legacy_override:
            raise RuntimeError(self.LEGACY_MESSAGE)
        super().save(*args, **kwargs)


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
        REPASSE = "repasse", "Repasse de Receita"

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
    carteira = models.ForeignKey(
        Carteira,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="lancamentos",
    )
    carteira_contraparte = models.ForeignKey(
        Carteira,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="lancamentos_contraparte",
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
            models.Index(
                fields=["carteira", "status", "data_vencimento"],
                name="idx_lanc_cart_status_venc",
            ),
            models.Index(fields=["carteira_contraparte"], name="idx_lanc_cart_contra"),
        ]

    def __str__(self) -> str:
        return f"{self.get_tipo_display()} - {self.valor}"

    @property
    def conta_associado_resolvida(self) -> ContaAssociado | None:
        """Retorna a conta associada considerando a carteira contraparte."""

        if getattr(self, "conta_associado_id", None):
            return getattr(self, "conta_associado", None)
        carteira_contra = getattr(self, "carteira_contraparte", None)
        if carteira_contra and getattr(carteira_contra, "conta_associado_id", None):
            return carteira_contra.conta_associado
        return None

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
    idempotency_key = models.CharField(max_length=255, unique=True, default=uuid.uuid4)

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
