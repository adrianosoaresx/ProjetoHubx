from django import forms
from django.contrib.auth import get_user_model
from django_select2 import forms as s2forms
from .models import Nucleo

User = get_user_model()


class NucleoForm(forms.ModelForm):
    membros = forms.ModelMultipleChoiceField(
        queryset=User.objects.all(), required=False, widget=forms.SelectMultiple
    )

    class Meta:
        model = Nucleo
        fields = ["organizacao", "nome", "descricao", "avatar", "membros"]


class NucleoWidget(s2forms.ModelSelect2Widget):
    search_fields = ["nome__icontains"]


class NucleoSearchForm(forms.Form):
    nucleo = forms.ModelChoiceField(
        queryset=Nucleo.objects.all(),
        required=False,
        label="",
        widget=NucleoWidget(
            attrs={
                "data-placeholder": "Buscar núcleos...",
                "data-minimum-input-length": 2,
            }
        ),
    )
