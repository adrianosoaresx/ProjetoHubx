from django import forms
from django.contrib.auth import get_user_model
from .models import Nucleo

User = get_user_model()


class NucleoForm(forms.ModelForm):
    membros = forms.ModelMultipleChoiceField(
        queryset=User.objects.all(), required=False, widget=forms.SelectMultiple
    )

    class Meta:
        model = Nucleo
        fields = ["organizacao", "nome", "descricao", "avatar", "membros"]
