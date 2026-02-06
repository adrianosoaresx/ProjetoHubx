from django import forms
from django.core.exceptions import ValidationError

from accounts.models import UserType

from .models import Organizacao
from .utils import validate_cnpj, validate_organizacao_image


class OrganizacaoForm(forms.ModelForm):
    class Meta:
        model = Organizacao
        fields = [
            "nome",
            "cnpj",
            "descricao",
            "tipo",
            "rua",
            "cidade",
            "estado",
            "cep",
            "contato_nome",
            "contato_email",
            "contato_telefone",
            "contato_whatsapp",
            "codigo_banco",
            "nome_banco",
            "agencia",
            "conta_corrente",
            "chave_pix",
            "mercado_pago_public_key",
            "mercado_pago_access_token",
            "mercado_pago_webhook_secret",
            "paypal_client_id",
            "paypal_client_secret",
            "paypal_webhook_secret",
            "paypal_currency",
            "valor_associacao",
            "valor_nucleacao",
            "dia_vencimento",
            "periodicidade",
            "nome_site",
            "site",
            "icone_site",
            "feed_noticias",
            "avatar",
        ]

    def __init__(self, *args, **kwargs) -> None:
        user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)
        self.payment_fields_hidden = False
        base_cls = "mt-1 w-full rounded-md border-gray-300 p-2"
        for field in self.fields.values():
            existing = field.widget.attrs.get("class", "")
            field.widget.attrs["class"] = f"{existing} {base_cls}".strip()
        for field_name in ["avatar", "icone_site"]:
            field = self.fields.get(field_name)
            if field:
                field.widget.attrs.setdefault("accept", "image/*")
                field.widget.attrs.setdefault("data-preview-target", f"preview-{field_name}")
                field.widget.attrs.setdefault("data-preview-placeholder", f"preview-placeholder-{field_name}")
        rua_field = self.fields.get("rua")
        if rua_field:
            rua_field.label = "Endereço"
        avatar_field = self.fields.get("avatar")
        if avatar_field:
            avatar_field.label = "Logotipo"
        if user and user.user_type != UserType.ROOT:
            payment_fields = [
                "mercado_pago_public_key",
                "mercado_pago_access_token",
                "mercado_pago_webhook_secret",
                "paypal_client_id",
                "paypal_client_secret",
                "paypal_webhook_secret",
            ]
            for field_name in payment_fields:
                self.fields.pop(field_name, None)
            self.payment_fields_hidden = True
            if user.user_type == UserType.ADMIN:
                self.fields.pop("paypal_currency", None)
            else:
                paypal_currency_field = self.fields.get("paypal_currency")
                if paypal_currency_field:
                    paypal_currency_field.disabled = True
                    paypal_currency_field.help_text = (
                        "Apenas usuários root podem editar a moeda do PayPal."
                    )
            cnpj_field = self.fields.get("cnpj")
            if cnpj_field:
                cnpj_field.disabled = True
                cnpj_field.help_text = "Apenas usuários root podem editar o CNPJ."

    def clean_cnpj(self):
        if self.fields["cnpj"].disabled:
            return self.instance.cnpj
        cnpj = validate_cnpj(self.cleaned_data.get("cnpj"))
        if Organizacao.objects.exclude(pk=self.instance.pk).filter(cnpj=cnpj).exists():
            raise forms.ValidationError("Uma organização com este CNPJ já existe.")
        return cnpj

    def clean_paypal_currency(self):
        field = self.fields.get("paypal_currency")
        if field and field.disabled:
            return self.instance.paypal_currency
        return self.cleaned_data.get("paypal_currency")

    def _clean_imagem(self, field_name: str):
        arquivo = self.cleaned_data.get(field_name)
        try:
            validate_organizacao_image(arquivo)
        except ValidationError as exc:
            raise forms.ValidationError(exc.messages) from exc
        return arquivo

    def clean_avatar(self):
        return self._clean_imagem("avatar")

    def clean_icone_site(self):
        return self._clean_imagem("icone_site")
