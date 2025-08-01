from django import forms
from django_select2 import forms as s2forms
from validate_docbr import CNPJ

from .models import ContatoEmpresa, Empresa, Tag


class EmpresaForm(forms.ModelForm):
    tags_field = forms.CharField(required=False, label="Tags")

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
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            self.fields["tags_field"].initial = ", ".join(self.instance.tags.values_list("nome", flat=True))
        self.initial.setdefault("organizacao", getattr(self.instance, "organizacao", None))
        self.initial.setdefault("usuario", getattr(self.instance, "usuario", None))

    def clean_cnpj(self):
        cnpj = self.cleaned_data["cnpj"]
        if not CNPJ().validate(cnpj):
            raise forms.ValidationError("CNPJ inválido")
        return cnpj

    def save(self, commit=True):
        instance = super().save(commit=False)
        if not instance.pk:
            instance.usuario = self.initial.get("usuario")
            instance.organizacao = self.initial.get("organizacao")
        if commit:
            instance.save()
        tags_names = [tag.strip() for tag in self.cleaned_data.get("tags_field", "").split(",") if tag.strip()]
        tags = []
        for name in tags_names:
            tag, _ = Tag.objects.get_or_create(nome=name)
            tags.append(tag)
        if commit:
            instance.tags.set(tags)
            self.save_m2m()
        else:
            self._save_m2m = lambda: instance.tags.set(tags)
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
        fields = ["nome", "categoria"]


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
