from django import forms

from .models import Organizacao


class OrganizacaoForm(forms.ModelForm):
    class Meta:
        model = Organizacao
        fields = ["nome", "cnpj", "descricao", "slug", "avatar", "cover"]

    def clean_cnpj(self):
        cnpj = self.cleaned_data.get("cnpj")
        if Organizacao.objects.exclude(pk=self.instance.pk).filter(cnpj=cnpj).exists():
            raise forms.ValidationError("Uma organização com este CNPJ já existe.")
        return cnpj
