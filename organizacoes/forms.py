from django import forms
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _

from .models import Organizacao
from .utils import validate_cnpj


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
            "rate_limit_multiplier",
        ]
        labels = {
            "rate_limit_multiplier": _("Multiplicador de limite de taxa"),
        }

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        base_cls = "mt-1 w-full rounded-md border-gray-300 p-2"
        for field in self.fields.values():
            existing = field.widget.attrs.get("class", "")
            field.widget.attrs["class"] = f"{existing} {base_cls}".strip()
        self.fields["slug"].required = False

    def clean_rate_limit_multiplier(self):
        mult = self.cleaned_data.get("rate_limit_multiplier")
        if mult is not None and mult <= 0:
            raise forms.ValidationError(_("Deve ser maior que zero."))
        return mult

    def clean_cnpj(self):
        cnpj = validate_cnpj(self.cleaned_data.get("cnpj"))
        if Organizacao.objects.exclude(pk=self.instance.pk).filter(cnpj=cnpj).exists():
            raise forms.ValidationError("Uma organização com este CNPJ já existe.")
        return cnpj

    def clean_slug(self):
        slug = self.cleaned_data.get("slug")
        nome = self.cleaned_data.get("nome")
        if not slug:
            slug = slugify(nome)
        else:
            slug = slugify(slug)
        base = slug
        counter = 2
        qs = Organizacao.objects.exclude(pk=self.instance.pk)
        while qs.filter(slug=slug).exists():
            slug = f"{base}-{counter}"
            counter += 1
        return slug
