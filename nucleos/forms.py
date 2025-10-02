from __future__ import annotations

import bleach
from django import forms
from django.utils.translation import gettext_lazy as _

from .models import Nucleo, ParticipacaoNucleo

class NucleoForm(forms.ModelForm):
    class Meta:
        model = Nucleo
        fields = [
            "nome",
            "descricao",
            "classificacao",
            "avatar",
            "cover",
            "mensalidade",
            "ativo",
        ]

    def clean_descricao(self):
        descricao = self.cleaned_data.get("descricao", "")
        return bleach.clean(descricao)

    def clean_mensalidade(self):
        valor = self.cleaned_data.get("mensalidade")
        if valor is not None and valor < 0:
            raise forms.ValidationError(_("Valor inválido"))
        return valor


class NucleoSearchForm(forms.Form):
    q = forms.CharField(label="", required=False)


class ParticipacaoForm(forms.ModelForm):
    class Meta:
        model = ParticipacaoNucleo
        fields = ["nucleo"]
        widgets = {"nucleo": forms.HiddenInput()}


class ParticipacaoDecisaoForm(forms.Form):
    acao = forms.CharField(widget=forms.HiddenInput())


class MembroRoleForm(forms.ModelForm):
    class Meta:
        model = ParticipacaoNucleo
        fields = ["papel"]
