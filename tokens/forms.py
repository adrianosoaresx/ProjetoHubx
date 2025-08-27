import pyotp
from django import forms
from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from nucleos.models import Nucleo
from organizacoes.models import Organizacao

from accounts.models import UserType
from .models import ApiToken, ApiTokenIp, CodigoAutenticacao, TokenAcesso
from .perms import can_issue_invite
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
            if user.user_type == UserType.ROOT:
                self.fields["organizacao"].queryset = Organizacao.objects.all()
                self.fields.pop("nucleos", None)
            else:
                self.fields["organizacao"].queryset = Organizacao.objects.filter(users=user)
                self.fields["nucleos"].queryset = Nucleo.objects.filter(
                    organizacao__users=user
                )

            self.fields["tipo_destino"].choices = [
                choice
                for choice in TokenAcesso.TipoUsuario.choices
                if can_issue_invite(user, choice[0])
            ]


class GerarApiTokenForm(forms.Form):
    client_name = forms.CharField(max_length=100, required=False, label=_("Nome do cliente"))
    scope = forms.ChoiceField(choices=ApiToken._meta.get_field("scope").choices, label=_("Escopo"))
    expires_in = forms.IntegerField(
        required=False,
        min_value=1,
        label=_("Validade (dias)"),
    )


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


class ApiTokenIpForm(forms.ModelForm):
    class Meta:
        model = ApiTokenIp
        fields = ["token", "ip", "tipo"]

    def __init__(self, *args, user: User | None = None, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)
        if user and not user.is_superuser:
            self.fields["token"].queryset = ApiToken.objects.filter(user=user)

    def clean_token(self):
        token = self.cleaned_data["token"]
        if not self.user:
            raise forms.ValidationError("Usuário inválido")
        if not self.user.is_superuser and token.user != self.user:
            raise forms.ValidationError("Token inválido")
        return token


class RemoverApiTokenIpForm(forms.Form):
    ip_id = forms.UUIDField()

    def __init__(self, *args, user: User | None = None, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)

    def save(self):
        ip_obj = get_object_or_404(ApiTokenIp, id=self.cleaned_data["ip_id"])
        if not self.user.is_superuser and ip_obj.token.user != self.user:
            raise forms.ValidationError("IP inválido")
        ip_obj.delete()
        return ip_obj
