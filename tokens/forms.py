import pyotp
from django import forms
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


from accounts.models import UserType

from .models import CodigoAutenticacao, TokenAcesso
from .perms import can_issue_invite
from .services import find_token_by_code

User = get_user_model()


GUEST_TOKEN_CHOICES = [
    (
        TokenAcesso.TipoUsuario.CONVIDADO.value,
        TokenAcesso.TipoUsuario.CONVIDADO.label,
    )
]


class TokenAcessoForm(forms.ModelForm):
    class Meta:
        model = TokenAcesso
        fields = ["tipo_destino"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["tipo_destino"].choices = GUEST_TOKEN_CHOICES


class GerarTokenConviteForm(forms.Form):
    tipo_destino = forms.ChoiceField(choices=GUEST_TOKEN_CHOICES)

    def __init__(self, *args, user=None, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)
        if user and not can_issue_invite(user, TokenAcesso.TipoUsuario.CONVIDADO.value):
            self.fields["tipo_destino"].choices = []


class ValidarTokenConviteForm(forms.Form):
    token = forms.CharField(
        max_length=64,
        label=_("Token de Convite"),
        widget=forms.TextInput(
            attrs={
                "class": "text-center font-mono tracking-widest",
                "placeholder": _("Token de convite"),
                "autofocus": True,
                "aria-describedby": "token_help",
            }
        ),
    )

    def clean_token(self):
        token_code = self.cleaned_data["token"]
        try:
            token = find_token_by_code(token_code)
        except TokenAcesso.DoesNotExist:
            raise forms.ValidationError(_("Token inválido"))
        if token.estado != TokenAcesso.Estado.NOVO:
            raise forms.ValidationError(_("Token inválido"))
        if token.data_expiracao and token.data_expiracao < timezone.now():
            raise forms.ValidationError(_("Token expirado"))
        self.token = token
        return token_code


class GerarCodigoAutenticacaoForm(forms.Form):
    def __init__(self, *args, usuario: User | None = None, **kwargs):
        self.usuario = usuario
        super().__init__(*args, **kwargs)

    def save(self, commit: bool = True) -> CodigoAutenticacao:
        codigo = CodigoAutenticacao(usuario=self.usuario)
        if commit:
            codigo.save()
        return codigo


class GerarCodigoAutenticacaoAdminForm(forms.Form):
    usuario = forms.ModelChoiceField(queryset=User.objects.all())

    def __init__(self, *args, user: User | None = None, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)
        if not self.user or not self.user.has_perm("tokens.add_codigoautenticacao"):
            from django.core.exceptions import PermissionDenied

            raise PermissionDenied

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
        self.codigo_obj = auth
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


