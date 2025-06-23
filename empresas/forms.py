from django import forms
from .models import Empresa, Tag


class EmpresaForm(forms.ModelForm):
    tags_field = forms.CharField(
        required=False,
        help_text="Separe as tags por v\u00edrgula",
        label="Produtos e Servi\u00e7os",
    )

    class Meta:
        model = Empresa
        fields = [
            "cnpj",
            "nome",
            "tipo",
            "municipio",
            "estado",
            "logo",
            "descricao",
            "contato",
            "palavras_chave",
            "tags_field",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            self.fields["tags_field"].initial = ", ".join(
                self.instance.tags.values_list("nome", flat=True)
            )

    def save(self, commit=True):
        instance = super().save(commit=False)
        if commit:
            instance.save()
        tags_names = [
            tag.strip() for tag in self.cleaned_data.get("tags_field", "").split(",") if tag.strip()
        ]
        tags = []
        for name in tags_names:
            tag, _created = Tag.objects.get_or_create(nome=name)
            tags.append(tag)
        if commit:
            instance.tags.set(tags)
            self.save_m2m()
        else:
            # if not commit we set relation after
            self._save_m2m = lambda: instance.tags.set(tags)
        return instance


class TagForm(forms.ModelForm):
    class Meta:
        model = Tag
        fields = ["nome", "categoria"]
