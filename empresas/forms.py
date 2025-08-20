import re

from django import forms
from django.utils.translation import gettext_lazy as _
from django_select2 import forms as s2forms
from validate_docbr import CNPJ

from .models import AvaliacaoEmpresa, ContatoEmpresa, Empresa, Tag


class TagMultipleWidget(s2forms.ModelSelect2MultipleWidget):
    search_fields = ["nome__icontains"]


class EmpresaForm(forms.ModelForm):
    tags = forms.ModelMultipleChoiceField(
        queryset=Tag.objects.all(),
        required=False,
        label=_("Tags"),
        widget=TagMultipleWidget(
            attrs={
                "data-placeholder": _("Buscar itens..."),
                "data-minimum-input-length": 2,
            }
        ),
    )

    class Meta:
        model = Empresa
        fields = [
            "nome",
            "cnpj",
            "tipo",
            "municipio",
            "estado",
            "logo",
            "descricao",
            "palavras_chave",
            "validado_em",
            "fonte_validacao",
            "tags",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            self.fields["tags"].initial = self.instance.tags.all()
        self.initial.setdefault("organizacao", getattr(self.instance, "organizacao", None))
        self.initial.setdefault("usuario", getattr(self.instance, "usuario", None))
        self.fields["validado_em"].disabled = True
        self.fields["fonte_validacao"].disabled = True

    def clean_cnpj(self):
        cnpj = re.sub(r"\D", "", self.cleaned_data["cnpj"])
        if not CNPJ().validate(cnpj):
            raise forms.ValidationError(_("CNPJ inválido"))
        mask = f"{cnpj[:2]}.{cnpj[2:5]}.{cnpj[5:8]}/{cnpj[8:12]}-{cnpj[12:14]}"
        qs = Empresa.objects.filter(cnpj=mask)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError(_("Empresa com este CNPJ já existe."))
        return mask

    def save(self, commit=True):
        instance = super().save(commit=False)
        if not instance.pk:
            instance.usuario = self.initial.get("usuario")
            instance.organizacao = self.initial.get("organizacao")
        tags = self.cleaned_data.get("tags")
        if commit:
            instance.save()
            if tags is not None:
                instance.tags.set(tags)
        else:
            self._save_m2m = lambda: instance.tags.set(tags or [])
        return instance


class ContatoEmpresaForm(forms.ModelForm):
    class Meta:
        model = ContatoEmpresa
        fields = [
            "nome",
            "cargo",
            "email",
            "telefone",
            "principal",
        ]

    def save(self, commit: bool = True):
        contato = super().save(commit=False)
        if contato.principal:
            ContatoEmpresa.objects.filter(empresa=contato.empresa, principal=True).exclude(pk=contato.pk).update(
                principal=False
            )
        if commit:
            contato.save()
        return contato


class TagForm(forms.ModelForm):
    class Meta:
        model = Tag
        fields = ["nome", "categoria", "parent"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["parent"].widget = TagWidget(
            attrs={
                "data-placeholder": _("Buscar item pai..."),
                "data-minimum-input-length": 2,
            }
        )


class EmpresaWidget(s2forms.ModelSelect2Widget):
    search_fields = [
        "nome__icontains",
        "descricao__icontains",
        "tags__nome__icontains",
        "palavras_chave__icontains",
    ]


class EmpresaSearchForm(forms.Form):
    empresa = forms.ModelChoiceField(
        queryset=Empresa.objects.all(),
        required=False,
        label="",
        widget=EmpresaWidget(
            attrs={
                "data-placeholder": "Buscar empresas...",
                "data-minimum-input-length": 2,
            }
        ),
    )


class TagWidget(s2forms.ModelSelect2Widget):
    search_fields = ["nome__icontains"]


class TagSearchForm(forms.Form):
    tag = forms.ModelChoiceField(
        queryset=Tag.objects.all(),
        required=False,
        label="",
        widget=TagWidget(
            attrs={
                "data-placeholder": "Buscar itens...",
                "data-minimum-input-length": 2,
            }
        ),
    )


class AvaliacaoForm(forms.ModelForm):
    class Meta:
        model = AvaliacaoEmpresa
        fields = ["nota", "comentario"]
