from __future__ import annotations

from decimal import Decimal

from django import forms
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from pagamentos.models import Transacao


class CheckoutForm(forms.Form):
    organizacao_id = forms.UUIDField(required=False, widget=forms.HiddenInput())
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
    pix_descricao = forms.CharField(label=_("Descrição do Pix"), max_length=140, required=False)
    pix_expiracao = forms.DateTimeField(
        label=_("Expiração do Pix"), required=False, widget=forms.DateTimeInput(attrs={"type": "datetime-local"})
    )
    cep = forms.CharField(label=_("CEP"), max_length=9, required=False)
    logradouro = forms.CharField(label=_("Logradouro"), max_length=120, required=False)
    numero = forms.CharField(label=_("Número"), max_length=20, required=False)
    bairro = forms.CharField(label=_("Bairro"), max_length=120, required=False)
    cidade = forms.CharField(label=_("Cidade"), max_length=120, required=False)
    estado = forms.CharField(label=_("Estado"), max_length=2, required=False)
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

    def clean_cep(self) -> str:
        cep = (self.cleaned_data.get("cep") or "").strip()
        if not cep:
            return cep
        digits = "".join(filter(str.isdigit, cep))
        if len(digits) != 8:
            raise forms.ValidationError(_("CEP deve ter 8 dígitos."))
        return digits

    def clean_estado(self) -> str:
        estado = (self.cleaned_data.get("estado") or "").strip()
        if not estado:
            return estado
        if len(estado) != 2 or not estado.isalpha():
            raise forms.ValidationError(_("Use a sigla de 2 letras para o estado."))
        return estado.upper()

    def clean(self):
        cleaned_data = super().clean()
        metodo = cleaned_data.get("metodo")
        if not metodo:
            return cleaned_data

        errors: dict[str, str] = {}

        if metodo == Transacao.Metodo.BOLETO:
            required_fields = [
                "vencimento",
                "cep",
                "logradouro",
                "numero",
                "bairro",
                "cidade",
                "estado",
                "documento",
            ]
            for field in required_fields:
                if not cleaned_data.get(field):
                    errors[field] = _("Campo obrigatório para boleto.")

            vencimento = cleaned_data.get("vencimento")
            if vencimento and vencimento <= timezone.now():
                errors["vencimento"] = _("A data de vencimento deve ser futura.")

        elif metodo == Transacao.Metodo.CARTAO:
            if not cleaned_data.get("token_cartao"):
                errors["token_cartao"] = _("Token do cartão é obrigatório.")
            if not cleaned_data.get("payment_method_id"):
                errors["payment_method_id"] = _("Informe a bandeira do cartão.")
            if not cleaned_data.get("documento"):
                errors["documento"] = _("Documento é obrigatório para cartão.")

        elif metodo == Transacao.Metodo.PIX:
            if not cleaned_data.get("documento"):
                errors["documento"] = _("Documento é obrigatório para Pix.")
            expiracao = cleaned_data.get("pix_expiracao")
            if expiracao and expiracao <= timezone.now():
                errors["pix_expiracao"] = _("Defina um prazo futuro para expiração do Pix.")

        for field, message in errors.items():
            self.add_error(field, message)
        return cleaned_data

    def _get_profile_data(self, user) -> dict[str, str]:
        if not user:
            return {"nome": "", "email": ""}

        nome = ""
        if hasattr(user, "get_full_name"):
            nome = user.get_full_name() or ""
        nome = nome or getattr(user, "name", "") or getattr(user, "username", "")
        email = getattr(user, "email", "") or ""
        return {"nome": nome, "email": email}
