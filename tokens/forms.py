from django import forms
from django.contrib.auth import get_user_model

from .models import TokenAcesso, CodigoAutenticacao, TOTPDevice

User = get_user_model()


class TokenAcessoForm(forms.ModelForm):
    class Meta:
        model = TokenAcesso
        fields = ["tipo_destino"]

    def __init__(self, *args, user=None, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)

        if user and user.tipo_id == User.Tipo.SUPERADMIN:
            self.fields["tipo_destino"].choices = [(TokenAcesso.Tipo.ADMIN, "admin")]
        elif user:
            self.fields["tipo_destino"].choices = [
                (TokenAcesso.Tipo.GERENTE, "gerente"),
                (TokenAcesso.Tipo.CLIENTE, "cliente"),
            ]

    def clean(self):
        cleaned = super().clean()
        if (
            self.user
            and self.user.tipo_id == User.Tipo.ADMIN
            and cleaned.get("tipo_destino")
            in {TokenAcesso.Tipo.GERENTE, TokenAcesso.Tipo.CLIENTE}
        ):
            self.add_error("nucleo_destino", "Selecione um núcleo")
        return cleaned


class GerarTokenConviteForm(forms.Form):
    tipo_destino = forms.ChoiceField(choices=TokenAcesso.TipoUsuario.choices)
    organizacao = forms.ModelChoiceField(queryset=None)  # TODO: Definir queryset
    nucleos = forms.ModelMultipleChoiceField(queryset=None, required=False)  # TODO: Definir queryset


class ValidarTokenConviteForm(forms.Form):
    codigo = forms.CharField(max_length=64)


class GerarCodigoAutenticacaoForm(forms.Form):
    usuario = forms.ModelChoiceField(queryset=None)  # TODO: Definir queryset


class ValidarCodigoAutenticacaoForm(forms.Form):
    codigo = forms.CharField(max_length=8)


class Ativar2FAForm(forms.Form):
    codigo_totp = forms.CharField(max_length=6)
