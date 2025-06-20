from django import forms
from .models import Organizacao


class OrganizacaoForm(forms.ModelForm):
    class Meta:
        model = Organizacao
        fields = ["nome", "cnpj", "descricao", "logo"]
