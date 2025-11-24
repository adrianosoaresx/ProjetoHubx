from __future__ import annotations

from decimal import Decimal

from django import forms
from django.utils import timezone
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

    def __init__(self, *args, user=None, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)
        profile_data = self._get_profile_data(user)
        for field_name, value in profile_data.items():
            if value and not self.initial.get(field_name):
                self.initial[field_name] = value
            if value and field_name in self.fields:
                self.fields[field_name].widget.attrs.update(
                    {"readonly": "readonly", "aria-readonly": "true"}
                )

        valor_field = self.fields.get("valor")
        if valor_field:
            valor_field.widget.attrs.update(
                {"readonly": "readonly", "aria-readonly": "true", "class": "bg-slate-50"}
            )

    def clean(self) -> dict[str, object]:
        cleaned = super().clean()
        if self.initial.get("valor") is not None:
            try:
                cleaned["valor"] = Decimal(self.initial["valor"])
            except Exception:
                self.add_error("valor", _("Valor inválido informado."))
        metodo = cleaned.get("metodo")
        if metodo == Transacao.Metodo.CARTAO:
            if not cleaned.get("token_cartao"):
                self.add_error("token_cartao", _("Token do cartão é obrigatório."))
        if metodo == Transacao.Metodo.BOLETO and not cleaned.get("vencimento"):
            self.add_error("vencimento", _("Data de vencimento é obrigatória."))
        if metodo == Transacao.Metodo.BOLETO and cleaned.get("vencimento"):
            vencimento = cleaned["vencimento"]
            if vencimento <= timezone.now():
                self.add_error("vencimento", _("A data de vencimento deve ser futura."))

        if self.user:
            profile_data = self._get_profile_data(self.user)
            nome_checkout = (cleaned.get("nome") or "").strip()
            if profile_data["nome"] and nome_checkout and nome_checkout != profile_data["nome"]:
                self.add_error(
                    "nome",
                    _("Use o nome cadastrado no seu perfil. Para alterar, edite as informações da conta."),
                )

            email_checkout = (cleaned.get("email") or "").strip().lower()
            if profile_data["email"] and email_checkout and email_checkout != profile_data["email"].lower():
                self.add_error(
                    "email",
                    _("Use o e-mail do seu perfil. Para atualizar, edite as informações da conta."),
                )

            documento_checkout = self._normalize_documento(cleaned.get("documento") or "")
            if profile_data["documento"] and documento_checkout:
                if documento_checkout != self._normalize_documento(profile_data["documento"]):
                    self.add_error(
                        "documento",
                        _("Use o CPF/CNPJ do seu perfil. Para corrigir, edite as informações da conta."),
                    )

        return cleaned

    def _get_profile_data(self, user) -> dict[str, str]:
        if not user:
            return {"nome": "", "email": "", "documento": ""}

        nome = ""
        if hasattr(user, "get_full_name"):
            nome = user.get_full_name() or ""
        nome = nome or getattr(user, "name", "") or getattr(user, "username", "")

        email = getattr(user, "email", "") or ""
        documento = getattr(user, "cpf", "") or getattr(user, "cnpj", "") or ""

        return {
            "nome": nome,
            "email": email,
            "documento": documento,
        }

    @staticmethod
    def _normalize_documento(documento: str) -> str:
        return "".join(char for char in documento if char.isdigit())
