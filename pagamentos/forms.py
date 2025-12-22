from __future__ import annotations

from decimal import Decimal

from django import forms
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from eventos.models import InscricaoEvento
from pagamentos.models import Transacao


class PixCheckoutForm(forms.Form):
    organizacao_id = forms.UUIDField(required=False, widget=forms.HiddenInput())
    inscricao_uuid = forms.UUIDField(required=False, widget=forms.HiddenInput())
    valor = forms.DecimalField(
        label=_("Valor"),
        min_value=Decimal("0.50"),
        max_digits=12,
        decimal_places=2,
        help_text=_("Informe o total a ser cobrado."),
    )
    metodo = forms.ChoiceField(label=_("Método"), choices=Transacao.Metodo.choices)
    nome = forms.CharField(label=_("Nome completo"), max_length=120)
    email = forms.EmailField(label=_("E-mail"))
    documento = forms.CharField(label=_("Documento"), max_length=40)
    parcelas = forms.IntegerField(label=_("Parcelas"), min_value=1, required=False, initial=1)
    token_cartao = forms.CharField(label=_("Token do cartão"), max_length=255, required=False)
    payment_method_id = forms.CharField(label=_("Bandeira do cartão"), max_length=50, required=False)
    vencimento = forms.DateTimeField(label=_("Vencimento do boleto"), required=False)
    pix_expiracao = forms.DateTimeField(
        label=_("Expiração do Pix"), required=False, widget=forms.DateTimeInput(attrs={"type": "datetime-local"})
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
            self.initial["metodo"] = Transacao.Metodo.PIX

    def clean_valor(self):
        valor = self.cleaned_data["valor"]
        if valor <= 0:
            raise forms.ValidationError(_("O valor deve ser maior que zero."))
        return valor

    def clean(self):
        cleaned_data = super().clean()
        errors: dict[str, str] = {}
        metodo = cleaned_data.get("metodo") or Transacao.Metodo.PIX
        cleaned_data["metodo"] = metodo

        if not cleaned_data.get("documento"):
            errors["documento"] = _("Documento é obrigatório para Pix.")

        expiracao = cleaned_data.get("pix_expiracao")
        if expiracao is None:
            errors["pix_expiracao"] = _("Informe o vencimento do Pix.")
        elif expiracao <= timezone.now():
            errors["pix_expiracao"] = _("Defina um prazo futuro para expiração do Pix.")

        if metodo == Transacao.Metodo.CARTAO:
            if not cleaned_data.get("token_cartao"):
                errors["token_cartao"] = _("Token do cartão é obrigatório.")
            if not cleaned_data.get("payment_method_id"):
                errors["payment_method_id"] = _("Informe a bandeira do cartão.")

        if metodo == Transacao.Metodo.BOLETO:
            if not cleaned_data.get("vencimento"):
                errors["vencimento"] = _("Data de vencimento obrigatória para boleto.")

        for field, message in errors.items():
            self.add_error(field, message)
        return cleaned_data

    def _get_profile_data(self, user) -> dict[str, str]:
        if not user:
            return {"nome": "", "email": "", "documento": ""}

        nome = ""
        if hasattr(user, "get_full_name"):
            nome = user.get_full_name() or ""
        nome = nome or getattr(user, "name", "") or getattr(user, "username", "")
        email = getattr(user, "email", "") or ""
        documento = getattr(user, "cpf", "") or getattr(user, "cnpj", "")
        return {"nome": nome, "email": email, "documento": documento}


class FaturamentoForm(forms.Form):
    CONDICAO_CHOICES = InscricaoEvento.CondicaoFaturamento.choices

    inscricao_uuid = forms.UUIDField(required=False, widget=forms.HiddenInput())
    organizacao_id = forms.UUIDField(required=False, widget=forms.HiddenInput())
    valor = forms.DecimalField(
        label=_("Valor"),
        min_value=Decimal("0.50"),
        max_digits=12,
        decimal_places=2,
        help_text=_("Informe o total a ser faturado."),
    )
    condicao_faturamento = forms.ChoiceField(
        label=_("Condição de faturamento"),
        choices=CONDICAO_CHOICES,
        required=False,
    )
    descricao = forms.CharField(
        label=_("Descrição"),
        max_length=255,
        required=False,
        help_text=_("Um rótulo curto para identificar o faturamento."),
    )

    def __init__(self, *args, organizacao=None, **kwargs):
        super().__init__(*args, **kwargs)
        if organizacao and organizacao.id:
            self.initial.setdefault("organizacao_id", organizacao.id)

    def clean_valor(self):
        valor = self.cleaned_data["valor"]
        if valor <= 0:
            raise forms.ValidationError(_("O valor deve ser maior que zero."))
        return valor

    def clean(self):
        cleaned_data = super().clean()
        errors: dict[str, str] = {}
        if not cleaned_data.get("inscricao_uuid"):
            errors["inscricao_uuid"] = _("Informe a inscrição para faturamento.")
        if not cleaned_data.get("condicao_faturamento"):
            errors["condicao_faturamento"] = _("Escolha uma condição de faturamento.")
        for field, message in errors.items():
            self.add_error(field, message)
        return cleaned_data
