from __future__ import annotations

from decimal import Decimal

from django import forms
from django.utils.translation import gettext_lazy as _

from pagamentos.models import Transacao


class CheckoutForm(forms.Form):
    valor = forms.DecimalField(
        label=_("Valor"),
        min_value=Decimal("0.50"),
        max_digits=12,
        decimal_places=2,
    )
    metodo = forms.ChoiceField(label=_("Método"), choices=Transacao.Metodo.choices)
    email = forms.EmailField(label=_("E-mail"))
    nome = forms.CharField(label=_("Nome"), max_length=100)
    documento = forms.CharField(label=_("Documento"), max_length=20)
    parcelas = forms.IntegerField(label=_("Parcelas"), min_value=1, required=False)
    token_cartao = forms.CharField(label=_("Token do cartão"), required=False)
    vencimento = forms.DateTimeField(label=_("Vencimento"), required=False)

    def clean(self) -> dict[str, object]:
        cleaned = super().clean()
        metodo = cleaned.get("metodo")
        if metodo == Transacao.Metodo.CARTAO:
            if not cleaned.get("token_cartao"):
                self.add_error("token_cartao", _("Token do cartão é obrigatório."))
        if metodo == Transacao.Metodo.BOLETO and not cleaned.get("vencimento"):
            self.add_error("vencimento", _("Data de vencimento é obrigatória."))
        return cleaned
