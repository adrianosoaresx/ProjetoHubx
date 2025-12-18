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
    )
    metodo = forms.ChoiceField(label=_("Método"), choices=Transacao.Metodo.choices)
    email = forms.EmailField(label=_("E-mail"))
    nome = forms.CharField(label=_("Nome"), max_length=100)
    documento = forms.CharField(label=_("Documento"), max_length=20)
    cep = forms.CharField(label=_("CEP"), max_length=9, required=False)
    logradouro = forms.CharField(label=_("Endereço"), max_length=100, required=False)
    numero = forms.CharField(label=_("Número"), max_length=10, required=False)
    bairro = forms.CharField(label=_("Bairro"), max_length=50, required=False)
    cidade = forms.CharField(label=_("Cidade"), max_length=50, required=False)
    estado = forms.CharField(label=_("Estado"), max_length=2, required=False)
    parcelas = forms.IntegerField(label=_("Parcelas"), min_value=1, required=False)
    token_cartao = forms.CharField(label=_("Token do cartão"), required=False)
    payment_method_id = forms.CharField(label=_("Bandeira do cartão"), required=False)
    vencimento = forms.DateTimeField(
        label=_("Vencimento"),
        required=False,
        widget=forms.DateInput(attrs={"type": "date"}),
        input_formats=("%Y-%m-%d", "%Y-%m-%dT%H:%M", "%Y-%m-%dT%H:%M:%S"),
    )

    def __init__(self, *args, user=None, organizacao=None, **kwargs):
        self.user = user
        self.organizacao = organizacao
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
        if valor_field and self.initial.get("valor") is not None:
            valor_field.widget.attrs.update(
                {"readonly": "readonly", "aria-readonly": "true", "class": "bg-slate-50"}
            )

        if organizacao and organizacao.id:
            self.initial.setdefault("organizacao_id", organizacao.id)

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
            if not (cleaned.get("payment_method_id") or "").strip():
                self.add_error(
                    "payment_method_id", _("A bandeira do cartão é obrigatória para processar o pagamento."),
                )
        if metodo == Transacao.Metodo.BOLETO:
            required_address_fields = {
                "cep": _("CEP é obrigatório para boleto."),
                "logradouro": _("Endereço é obrigatório para boleto."),
                "numero": _("Número é obrigatório para boleto."),
                "bairro": _("Bairro é obrigatório para boleto."),
                "cidade": _("Cidade é obrigatória para boleto."),
                "estado": _("Estado é obrigatório para boleto."),
            }
            for field_name, message in required_address_fields.items():
                if not (cleaned.get(field_name) or "").strip():
                    self.add_error(field_name, message)

            cep_value = cleaned.get("cep")
            if cep_value:
                cep_digits = "".join(char for char in cep_value if char.isdigit())
                if len(cep_digits) != 8:
                    self.add_error("cep", _("Informe um CEP válido com 8 dígitos."))
                else:
                    cleaned["cep"] = cep_digits

            estado_value = (cleaned.get("estado") or "").strip().upper()
            if estado_value:
                if len(estado_value) != 2 or not estado_value.isalpha():
                    self.add_error("estado", _("Informe a sigla do estado com 2 letras."))
                else:
                    cleaned["estado"] = estado_value

            if not cleaned.get("vencimento"):
                self.add_error("vencimento", _("Data de vencimento é obrigatória."))
            if cleaned.get("vencimento"):
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
