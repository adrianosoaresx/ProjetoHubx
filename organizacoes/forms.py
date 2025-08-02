from django import forms
from django.utils.text import slugify

from .models import Organizacao


class OrganizacaoForm(forms.ModelForm):
    class Meta:
        model = Organizacao
        fields = [
            "nome",
            "cnpj",
            "descricao",
            "slug",
            "tipo",
            "rua",
            "cidade",
            "estado",
            "contato_nome",
            "contato_email",
            "contato_telefone",
            "avatar",
            "cover",
        ]

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        base_cls = "mt-1 w-full rounded-md border-gray-300 p-2"
        for field in self.fields.values():
            existing = field.widget.attrs.get("class", "")
            field.widget.attrs["class"] = f"{existing} {base_cls}".strip()

    def clean_cnpj(self):
        cnpj = self.cleaned_data.get("cnpj")
        if Organizacao.objects.exclude(pk=self.instance.pk).filter(cnpj=cnpj).exists():
            raise forms.ValidationError("Uma organização com este CNPJ já existe.")
        return cnpj

    def clean_slug(self):
        slug = self.cleaned_data.get("slug")
        if slug:
            slug = slugify(slug)
            if Organizacao.objects.exclude(pk=self.instance.pk).filter(slug=slug).exists():
                raise forms.ValidationError("Este slug já está em uso.")
        return slug
