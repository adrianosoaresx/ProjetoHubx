import pyotp
from django import forms
from django.contrib.auth import get_user_model
from django.utils import timezone

from nucleos.models import Nucleo
from organizacoes.models import Organizacao

from .models import CodigoAutenticacao, TokenAcesso
from .services import find_token_by_code

User = get_user_model()


class TokenAcessoForm(forms.ModelForm):
    class Meta:
        model = TokenAcesso
        fields = ["tipo_destino"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["tipo_destino"].choices = TokenAcesso.TipoUsuario.choices


class GerarTokenConviteForm(forms.Form):
    tipo_destino = forms.ChoiceField(choices=TokenAcesso.TipoUsuario.choices)
    organizacao = forms.ModelChoiceField(queryset=None)
    nucleos = forms.ModelMultipleChoiceField(queryset=None, required=False)

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        if user:
            self.fields["organizacao"].queryset = Organizacao.objects.filter(users=user)
            self.fields["nucleos"].queryset = Nucleo.objects.filter(organizacao__users=user)


class ValidarTokenConviteForm(forms.Form):
    codigo = forms.CharField(max_length=32)

    def clean_codigo(self):
        codigo = self.cleaned_data["codigo"]
        try:
            token = find_token_by_code(codigo)
        except TokenAcesso.DoesNotExist:
            raise forms.ValidationError("Token inválido")
        if token.estado != TokenAcesso.Estado.NOVO:
            raise forms.ValidationError("Token inválido")
        if token.data_expiracao and token.data_expiracao < timezone.now():
            raise forms.ValidationError("Token expirado")
        self.token = token
        return codigo


class GerarCodigoAutenticacaoForm(forms.Form):
    usuario = forms.ModelChoiceField(queryset=User.objects.all())

    def save(self, commit: bool = True) -> CodigoAutenticacao:
        codigo = CodigoAutenticacao(usuario=self.cleaned_data["usuario"])
        if commit:
            codigo.save()
        return codigo


class ValidarCodigoAutenticacaoForm(forms.Form):
    codigo = forms.CharField(max_length=8)

    def __init__(self, *args, usuario: User | None = None, **kwargs):
        self.usuario = usuario
        super().__init__(*args, **kwargs)

    def clean_codigo(self):
        codigo = self.cleaned_data["codigo"]
        try:
            auth = CodigoAutenticacao.objects.filter(usuario=self.usuario, verificado=False).latest("created_at")
        except CodigoAutenticacao.DoesNotExist:
            raise forms.ValidationError("Código inválido")
        if auth.tentativas >= 3:
            raise forms.ValidationError("Código bloqueado")
        if auth.is_expirado():
            raise forms.ValidationError("Código expirado")
        if not auth.check_codigo(codigo):
            auth.tentativas += 1
            auth.save(update_fields=["tentativas"])
            raise forms.ValidationError("Código incorreto")
        auth.verificado = True
        auth.save(update_fields=["verificado"])
        return codigo


class Ativar2FAForm(forms.Form):
    codigo_totp = forms.CharField(max_length=6)

    def __init__(self, *args, user: User | None = None, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)

    def clean_codigo_totp(self):
        codigo = self.cleaned_data["codigo_totp"]
        if not self.user or not self.user.two_factor_secret:
            raise forms.ValidationError("Secret inválido")
        if not pyotp.TOTP(self.user.two_factor_secret).verify(codigo):
            raise forms.ValidationError("Código inválido")
        return codigo
