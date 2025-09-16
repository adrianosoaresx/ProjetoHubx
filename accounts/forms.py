import re

import pyotp
from django import forms
from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.forms import UserChangeForm, UserCreationForm
from django.core.cache import cache
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from tokens.models import TOTPDevice
from tokens.utils import get_client_ip

from .models import AccountToken, SecurityEvent, UserMedia
from .tasks import send_confirmation_email
from .validators import cpf_validator

User = get_user_model()


class CustomUserCreationForm(UserCreationForm):
    """Formulário de criação de usuário usando email como login."""

    class Meta(UserCreationForm.Meta):
        model = User
        fields = (
            "email",
            "cpf",
            "avatar",
            "first_name",
            "last_name",
            "biografia",
            "cover",
            "phone_number",
            "whatsapp",
            "redes_sociais",
            "organizacao",
            "nucleo",
        )

    def clean_email(self):
        email = self.cleaned_data.get("email")
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("Este e-mail já está em uso.")
        return email

    def clean_cpf(self):
        cpf = self.cleaned_data.get("cpf")
        if not cpf:
            return cpf
        cpf_validator(cpf)
        return cpf

    def clean_whatsapp(self):
        whatsapp = self.cleaned_data.get("whatsapp")
        if whatsapp and not re.match(r"^\+?\d{8,20}$", whatsapp):
            raise forms.ValidationError("WhatsApp deve ser válido.")
        return whatsapp

    def save(self, commit: bool = True) -> User:
        user = super().save(commit=False)
        user.is_active = False
        user.email_confirmed = False
        if commit:
            user.save()
            token = AccountToken.objects.create(
                usuario=user,
                tipo=AccountToken.Tipo.EMAIL_CONFIRMATION,
                expires_at=timezone.now() + timezone.timedelta(hours=24),
            )
            send_confirmation_email.delay(token.id)
        return user


class CustomUserChangeForm(UserChangeForm):
    class Meta:
        model = User
        fields = (
            "email",
            "cpf",
            "avatar",
            "first_name",
            "last_name",
            "biografia",
            "cover",
            "phone_number",
            "whatsapp",
            "redes_sociais",
            "organizacao",
            "nucleo",
        )


class InformacoesPessoaisForm(forms.ModelForm):
    first_name = forms.CharField(max_length=150, label="Nome")
    last_name = forms.CharField(max_length=150, label="Sobrenome")
    cpf = forms.CharField(max_length=14, required=False, label="CPF", validators=[cpf_validator])
    facebook = forms.URLField(required=False, label=_("Facebook"), assume_scheme="https")
    twitter = forms.URLField(required=False, label=_("Twitter"), assume_scheme="https")
    instagram = forms.URLField(required=False, label=_("Instagram"), assume_scheme="https")
    linkedin = forms.URLField(required=False, label=_("LinkedIn"), assume_scheme="https")

    class Meta:
        model = User
        fields = (
            "first_name",
            "last_name",
            "username",
            "email",
            "cpf",
            "avatar",
            "cover",
            "biografia",
            "phone_number",
            "whatsapp",
            "endereco",
            "cidade",
            "estado",
            "cep",
        )

    field_order = (
        "first_name",
        "last_name",
        "username",
        "email",
        "cpf",
        "avatar",
        "cover",
        "biografia",
        "phone_number",
        "whatsapp",
        "endereco",
        "cidade",
        "estado",
        "cep",
        "facebook",
        "twitter",
        "instagram",
        "linkedin",
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.order_fields(self.field_order)
        if self.instance.pk:
            self.initial["first_name"] = self.instance.first_name
            self.initial["last_name"] = self.instance.last_name
            self.initial["cpf"] = self.instance.cpf
            self.original_email = self.instance.email
        else:
            self.original_email = None
        redes = getattr(self.instance, "redes_sociais", None) or {}
        for field in ("facebook", "twitter", "instagram", "linkedin"):
            if redes.get(field):
                self.fields[field].initial = redes[field]

    def clean_cpf(self):
        cpf = self.cleaned_data.get("cpf")
        if cpf and User.objects.exclude(pk=self.instance.pk).filter(cpf=cpf).exists():
            raise forms.ValidationError(_("CPF já cadastrado."))
        return cpf

    def save(self, commit: bool = True) -> User:
        user = super().save(commit=False)
        user.first_name = self.cleaned_data.get("first_name", "")
        user.last_name = self.cleaned_data.get("last_name", "")
        user.cpf = self.cleaned_data.get("cpf")
        redes = {}
        for field in ("facebook", "twitter", "instagram", "linkedin"):
            value = self.cleaned_data.get(field)
            if value:
                redes[field] = value
        user.redes_sociais = redes
        self.email_changed = self.original_email and self.cleaned_data.get("email") != self.original_email
        if self.email_changed:
            user.is_active = False
            user.email_confirmed = False
        if commit:
            user.save()
            if self.email_changed:
                AccountToken.objects.filter(
                    usuario=user,
                    tipo=AccountToken.Tipo.EMAIL_CONFIRMATION,
                    used_at__isnull=True,
                ).update(used_at=timezone.now())
                token = AccountToken.objects.create(
                    usuario=user,
                    tipo=AccountToken.Tipo.EMAIL_CONFIRMATION,
                    expires_at=timezone.now() + timezone.timedelta(hours=24),
                )
                send_confirmation_email.delay(token.id)
        return user


class MediaForm(forms.ModelForm):
    tags_field = forms.CharField(
        required=False,
        help_text="Separe as tags por vírgula",
        label="Tags",
    )

    class Meta:
        model = UserMedia
        fields = ("file", "descricao", "publico", "tags_field")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            self.fields["tags_field"].initial = ", ".join(self.instance.tags.values_list("nome", flat=True))

    def save(self, commit=True):
        instance = super().save(commit=False)
        if commit:
            instance.save()
        tags_field = self.cleaned_data.get("tags_field", "")
        tags_names: list[str] = []
        for t in tags_field.split(","):
            name = t.strip().lower()
            if name and name not in tags_names:
                tags_names.append(name)
        from .models import MediaTag

        tags = []
        for name in tags_names:
            tag, _ = MediaTag.objects.get_or_create(nome__iexact=name, defaults={"nome": name})
            tags.append(tag)
        if commit:
            instance.tags.set(tags)
            self.save_m2m()
        else:
            self._save_m2m = lambda: instance.tags.set(tags)
        return instance


class EmailLoginForm(forms.Form):
    email = forms.EmailField(label="Email")
    password = forms.CharField(widget=forms.PasswordInput, label="Senha")
    totp = forms.CharField(
        label="TOTP", required=False, help_text=_("Deixe em branco se não tiver 2FA")
    )

    def __init__(self, request=None, *args, **kwargs):
        self.request = request
        self.user = None
        super().__init__(*args, **kwargs)

    def clean(self):
        email = self.cleaned_data.get("email")
        password = self.cleaned_data.get("password")
        totp = self.cleaned_data.get("totp")
        if not email or not password:
            raise forms.ValidationError("Informe e-mail e senha.")
        try:
            user = User.objects.get(email__iexact=email)
        except User.DoesNotExist:
            authenticate(self.request, username=email, password=password)
            raise forms.ValidationError("Credenciais inválidas.")
        lock_key = f"lockout_user_{user.pk}"
        lock_until = cache.get(lock_key)
        now = timezone.now()
        if lock_until and lock_until > now:
            authenticate(self.request, username=email, password=password)
            SecurityEvent.objects.create(
                usuario=user,
                evento="login_bloqueado",
                ip=get_client_ip(self.request) if self.request else None,
            )
            raise forms.ValidationError(f"Conta bloqueada. Tente novamente após {lock_until.strftime('%H:%M')}")
        if not user.is_active:
            raise forms.ValidationError("Conta inativa. Confirme seu e-mail.")
        if not user.check_password(password):
            authenticate(self.request, username=email, password=password)
            raise forms.ValidationError("Credenciais inválidas.")
        if user.two_factor_enabled and TOTPDevice.objects.filter(usuario=user).exists():
            if not totp:
                raise forms.ValidationError("Código de verificação obrigatório.")
            if not pyotp.TOTP(user.two_factor_secret).verify(totp):
                authenticate(self.request, username=email, password=password, totp=totp)
                raise forms.ValidationError("Código de verificação inválido.")
        auth_user = authenticate(self.request, username=email, password=password, totp=totp)
        if auth_user is None:
            raise forms.ValidationError("Credenciais inválidas.")
        self.user = auth_user
        return self.cleaned_data

    def get_user(self):
        return self.user
