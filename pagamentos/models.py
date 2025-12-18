from __future__ import annotations

from decimal import Decimal

from django.db import models
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from payments import PurchasedItem
from payments.models import BasePayment

from organizacoes.models import Organizacao


class Pedido(models.Model):
    class Status(models.TextChoices):
        PENDENTE = "pending", _("Pendente")
        PAGO = "paid", _("Pago")
        CANCELADO = "cancelled", _("Cancelado")

    organizacao: Organizacao | None = models.ForeignKey(
        Organizacao,
        verbose_name=_("Organização"),
        related_name="pedidos",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
    )
    valor: Decimal = models.DecimalField(verbose_name=_("Valor"), max_digits=12, decimal_places=2)
    status: str = models.CharField(
        verbose_name=_("Status"),
        max_length=20,
        choices=Status.choices,
        default=Status.PENDENTE,
    )
    email: str | None = models.EmailField(verbose_name=_("E-mail do cliente"), blank=True, null=True)
    nome: str | None = models.CharField(verbose_name=_("Nome do cliente"), max_length=120, blank=True, null=True)
    documento: str | None = models.CharField(verbose_name=_("Documento"), max_length=40, blank=True, null=True)
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
    class Metodo(models.TextChoices):
        PIX = "pix", _("Pix")
        CARTAO = "card", _("Cartão de crédito")
        BOLETO = "boleto", _("Boleto bancário")
        PAYPAL = "paypal", _("PayPal")

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
    metodo: str = models.CharField(
        verbose_name=_("Método"), max_length=20, choices=Metodo.choices
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
    detalhes: dict | None = models.JSONField(
        verbose_name=_("Detalhes da transação"), default=dict, blank=True, null=True
    )
    criado_em = models.DateTimeField(verbose_name=_("Criado em"), auto_now_add=True)
    atualizado_em = models.DateTimeField(verbose_name=_("Atualizado em"), auto_now=True)

    class Meta:
        verbose_name = _("Transação")
        verbose_name_plural = _("Transações")
        ordering = ("-criado_em",)

    def __str__(self) -> str:
        return f"{self._meta.verbose_name} #{self.pk}"

    @property
    def pix_qr_code(self) -> str | None:
        transaction_data = self._transaction_data
        return transaction_data.get("qr_code") if transaction_data else None

    @property
    def pix_qr_code_base64(self) -> str | None:
        transaction_data = self._transaction_data
        return transaction_data.get("qr_code_base64") if transaction_data else None

    @property
    def boleto_url(self) -> str | None:
        transaction_details = (self.detalhes or {}).get("transaction_details", {})
        return transaction_details.get("external_resource_url")

    @property
    def boleto_expiracao(self) -> str | None:
        return (self.detalhes or {}).get("date_of_expiration")

    @property
    def paypal_approval_url(self) -> str | None:
        if self.metodo != Transacao.Metodo.PAYPAL:
            return None
        links = (self.detalhes or {}).get("links") or []
        for link in links:
            if link.get("rel") == "approve":
                return link.get("href")
        return None

    @property
    def _transaction_data(self) -> dict | None:
        return (self.detalhes or {}).get("point_of_interaction", {}).get("transaction_data")


class Pagamento(BasePayment):
    pedido: Pedido | None = models.ForeignKey(
        Pedido,
        related_name="pagamentos",
        verbose_name=_("Pedido"),
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )

    class Meta:
        verbose_name = _("Pagamento")
        verbose_name_plural = _("Pagamentos")

    def get_purchased_items(self) -> list[PurchasedItem]:
        return [
            PurchasedItem(
                name=self.description or str(self.pedido) or _("Pagamento Hubx"),
                sku=str(self.pedido_id or self.pk),
                quantity=1,
                price=self.total,
                currency=self.currency,
            )
        ]

    def get_failure_url(self) -> str:
        return reverse("pagamentos:mercadopago-retorno", kwargs={"status": "falha"}) + f"?token={self.token}"

    def get_success_url(self) -> str:
        return reverse("pagamentos:mercadopago-retorno", kwargs={"status": "sucesso"}) + f"?token={self.token}"
