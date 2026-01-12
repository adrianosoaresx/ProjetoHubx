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
            "contato_nome",
            "contato_email",
            "contato_telefone",
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
            "nome_site",
            "site",
            "icone_site",
            "feed_noticias",
            "avatar",
            "cover",
        ]

    def __init__(self, *args, **kwargs) -> None:
        user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)
        self.payment_fields_hidden = False
        base_cls = "mt-1 w-full rounded-md border-gray-300 p-2"
        for field in self.fields.values():
            existing = field.widget.attrs.get("class", "")
            field.widget.attrs["class"] = f"{existing} {base_cls}".strip()
        for field_name in ["avatar", "cover", "icone_site"]:
            field = self.fields.get(field_name)
            if field:
                field.widget.attrs.setdefault("accept", "image/*")
                field.widget.attrs.setdefault("data-preview-target", f"preview-{field_name}")
                field.widget.attrs.setdefault("data-preview-placeholder", f"preview-placeholder-{field_name}")
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

    def _clean_imagem(self, field_name: str):
        arquivo = self.cleaned_data.get(field_name)
        try:
            validate_organizacao_image(arquivo)
        except ValidationError as exc:
            raise forms.ValidationError(exc.messages) from exc
        return arquivo

    def clean_avatar(self):
        return self._clean_imagem("avatar")

    def clean_cover(self):
        return self._clean_imagem("cover")

    def clean_icone_site(self):
        return self._clean_imagem("icone_site")
