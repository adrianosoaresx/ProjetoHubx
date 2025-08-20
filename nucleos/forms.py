from __future__ import annotations

import bleach
from django import forms
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _

from .models import CoordenadorSuplente, Nucleo, ParticipacaoNucleo

User = get_user_model()


class NucleoForm(forms.ModelForm):
    class Meta:
        model = Nucleo
        fields = ["nome", "slug", "descricao", "avatar", "cover", "ativo"]

    def clean_descricao(self):
        descricao = self.cleaned_data.get("descricao", "")
        return bleach.clean(descricao)


class NucleoSearchForm(forms.Form):
    q = forms.CharField(label="", required=False)


class ParticipacaoForm(forms.ModelForm):
    class Meta:
        model = ParticipacaoNucleo
        fields = ["nucleo"]
        widgets = {"nucleo": forms.HiddenInput()}


class ParticipacaoDecisaoForm(forms.Form):
    acao = forms.CharField(widget=forms.HiddenInput())


class SuplenteForm(forms.ModelForm):
    class Meta:
        model = CoordenadorSuplente
        fields = ["usuario", "periodo_inicio", "periodo_fim"]

    def __init__(self, *args, nucleo: Nucleo | None = None, **kwargs):
        super().__init__(*args, **kwargs)
        if nucleo is not None:
            self.fields["usuario"].queryset = nucleo.membros.order_by(
                "first_name", "last_name"
            )
        else:
            self.fields["usuario"].queryset = User.objects.none()

    def clean(self):
        data = super().clean()
        inicio = data.get("periodo_inicio")
        fim = data.get("periodo_fim")
        if inicio and fim and inicio >= fim:
            raise forms.ValidationError(_("Período inválido"))
        return data


class MembroRoleForm(forms.ModelForm):
    class Meta:
        model = ParticipacaoNucleo
        fields = ["papel"]
