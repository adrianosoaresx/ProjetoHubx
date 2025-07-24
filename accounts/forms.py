from __future__ import annotations

from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserChangeForm, UserCreationForm
from django.core.validators import RegexValidator

from .models import ConfiguracaoDeConta

User = get_user_model()

cpf_validator = RegexValidator(r"^\d{3}\.\d{3}\.\d{3}-\d{2}$", "CPF inválido. Use 000.000.000-00")


class CustomUserCreationForm(UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model = User
        fields = [
            "username",
            "email",
            "nome_completo",
            "cpf",
            "organizacao",
            "is_associado",
            "nucleos",
            "avatar",
            "cover",
            "biografia",
            "endereco",
            "estado",
            "cep",
            "fone",
            "whatsapp",
            "redes_sociais",
        ]

    def clean_cpf(self) -> str:
        cpf = self.cleaned_data.get("cpf", "")
        cpf_validator(cpf)
        return cpf


class CustomUserChangeForm(UserChangeForm):
    class Meta:
        model = User
        fields = [
            "username",
            "email",
            "nome_completo",
            "cpf",
            "organizacao",
            "is_associado",
            "nucleos",
            "avatar",
            "cover",
            "biografia",
            "endereco",
            "estado",
            "cep",
            "fone",
            "whatsapp",
            "redes_sociais",
        ]

    def clean_cpf(self) -> str:
        cpf = self.cleaned_data.get("cpf", "")
        cpf_validator(cpf)
        return cpf


class ConfiguracaoContaForm(forms.ModelForm):
    class Meta:
        model = ConfiguracaoDeConta
        fields = [
            "receber_notificacoes_email",
            "receber_notificacoes_whatsapp",
            "tema_escuro",
        ]


class InformacoesPessoaisForm(forms.ModelForm):
    class Meta:
        model = User
        fields = [
            "nome_completo",
            "username",
            "email",
            "avatar",
            "cover",
            "biografia",
            "fone",
            "whatsapp",
            "endereco",
            "estado",
            "cep",
        ]


class RedesSociaisForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ["redes_sociais"]


class NotificacoesForm(forms.ModelForm):
    class Meta:
        model = ConfiguracaoDeConta
        exclude = ["user"]
