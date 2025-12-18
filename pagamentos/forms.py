from __future__ import annotations

from decimal import Decimal

from django import forms
from django.conf import settings
from django.utils.translation import gettext_lazy as _


class CheckoutForm(forms.Form):
    organizacao_id = forms.UUIDField(required=False, widget=forms.HiddenInput())
    valor = forms.DecimalField(
        label=_("Valor"),
        min_value=Decimal("0.50"),
        max_digits=12,
        decimal_places=2,
        help_text=_("Informe o total a ser cobrado."),
    )
    metodo = forms.ChoiceField(
        label=_("Método"), choices=getattr(settings, "CHECKOUT_PAYMENT_CHOICES", ()), initial="mercadopago"
    )
    nome_completo = forms.CharField(label=_("Nome completo"), max_length=120)
    email = forms.EmailField(label=_("E-mail"))
    descricao = forms.CharField(
        label=_("Descrição"),
        max_length=255,
        required=False,
        help_text=_("Um rótulo curto para identificar o pagamento."),
    )

    def __init__(self, *args, user=None, organizacao=None, **kwargs):
        self.user = user
        self.organizacao = organizacao
        super().__init__(*args, **kwargs)
        profile_data = self._get_profile_data(user)
        if organizacao and organizacao.id:
            self.initial.setdefault("organizacao_id", organizacao.id)
        for field_name, value in profile_data.items():
            if value and field_name in self.fields:
                self.initial.setdefault(field_name, value)
        if not self.initial.get("metodo") and self.fields["metodo"].choices:
            self.initial["metodo"] = self.fields["metodo"].choices[0][0]

    def clean_valor(self):
        valor = self.cleaned_data["valor"]
        if valor <= 0:
            raise forms.ValidationError(_("O valor deve ser maior que zero."))
        return valor

    def _get_profile_data(self, user) -> dict[str, str]:
        if not user:
            return {"nome_completo": "", "email": ""}

        nome = ""
        if hasattr(user, "get_full_name"):
            nome = user.get_full_name() or ""
        nome = nome or getattr(user, "name", "") or getattr(user, "username", "")
        email = getattr(user, "email", "") or ""
        return {"nome_completo": nome, "email": email}
