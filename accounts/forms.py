import re

import pyotp
from django import forms
from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.forms import UserChangeForm, UserCreationForm
from django.forms import ClearableFileInput
from django.core.cache import cache
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db.models import Q
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from tokens.models import TOTPDevice
from tokens.utils import get_client_ip

from .models import AREA_ATUACAO_CHOICES, AccountToken, SecurityEvent
from .tasks import send_confirmation_email
from .validators import cpf_validator
from organizacoes.utils import validate_cnpj

User = get_user_model()


CPF_REUSE_ERROR = _("Para reutilizar este CPF, informe também um CNPJ válido.")
IDENTIFIER_REQUIRED_ERROR = _("Informe CPF ou CNPJ.")


def _get_field_value(form: forms.BaseForm, field_name: str) -> str:
    """Return the raw or cleaned value for ``field_name`` respecting prefixes."""

    value = form.cleaned_data.get(field_name)
    if value not in (None, ""):
        return value
    prefixed_name = form.add_prefix(field_name)
    return form.data.get(prefixed_name, form.data.get(field_name, ""))


def _validate_cpf_reuse(form: forms.BaseForm, cpf: str, *, exclude_pk=None) -> None:
    """Ensure CPF reuse obeys the CNPJ requirements."""

    if not cpf:
        return
    qs = User.objects.all()
    if exclude_pk:
        qs = qs.exclude(pk=exclude_pk)
    matches = qs.filter(cpf=cpf)
    if not matches.exists():
        return
    cnpj_value = (_get_field_value(form, "cnpj") or "").strip()
    if not cnpj_value:
        raise forms.ValidationError(CPF_REUSE_ERROR)
    if matches.filter(Q(cnpj__isnull=True) | Q(cnpj="")).exists():
        raise forms.ValidationError(CPF_REUSE_ERROR)


class ProfileImageFileInput(ClearableFileInput):
    template_name = "accounts/widgets/profile_image_file_input.html"

    def __init__(self, *, button_label: str, empty_label: str, attrs=None):
        default_attrs = {"accept": "image/*"}
        if attrs:
            default_attrs.update(attrs)
        super().__init__(attrs=default_attrs)
        self.button_label = button_label
        self.empty_label = empty_label

    def get_context(self, name, value, attrs):
        context = super().get_context(name, value, attrs)
        widget = context["widget"]
        widget["button_label"] = self.button_label
        widget["empty_label"] = self.empty_label

        final_attrs = widget.get("attrs", {})
        classes = final_attrs.get("class", "").split()
        if "sr-only" not in classes:
            classes.append("sr-only")
        final_attrs["class"] = " ".join(filter(None, classes))
        final_attrs.setdefault("data-profile-file-input", "true")
        final_attrs["data-empty-text"] = self.empty_label
        widget["attrs"] = final_attrs

        value_name = ""
        if value:
            if hasattr(value, "name"):
                value_name = value.name or ""
            else:
                value_name = str(value)
        widget["value_name"] = value_name
        return context


class CustomUserCreationForm(UserCreationForm):
    """Formulário de criação de usuário usando email como login."""

    class Meta(UserCreationForm.Meta):
        model = User
        fields = (
            "email",
            "cpf",
            "cnpj",
            "razao_social",
            "nome_fantasia",
            "avatar",
            "contato",
            "biografia",
            "cover",
            "phone_number",
            "whatsapp",
            "birth_date",
            "redes_sociais",
            "organizacao",
            "nucleo",
            "area_atuacao",
            "descricao_atividade",
        )
        labels = {"contato": "Contato"}
        widgets = {
            "birth_date": forms.DateInput(format="%Y-%m-%d", attrs={"type": "date"})
        }

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
        _validate_cpf_reuse(self, cpf)
        return cpf

    def clean_cnpj(self):
        cnpj = self.cleaned_data.get("cnpj")
        if not cnpj:
            return cnpj
        try:
            cnpj = validate_cnpj(cnpj)
        except DjangoValidationError as exc:
            raise forms.ValidationError(exc.messages)
        if User.objects.filter(cnpj=cnpj).exists():
            raise forms.ValidationError(_("CNPJ já cadastrado."))
        return cnpj

    def clean(self):
        cleaned_data = super().clean()
        cpf_raw = (_get_field_value(self, "cpf") or "").strip()
        cnpj_raw = (_get_field_value(self, "cnpj") or "").strip()
        if not cpf_raw and not cnpj_raw:
            self.add_error("cpf", IDENTIFIER_REQUIRED_ERROR)
            self.add_error("cnpj", IDENTIFIER_REQUIRED_ERROR)
            raise forms.ValidationError(IDENTIFIER_REQUIRED_ERROR)
        return cleaned_data

    def clean_whatsapp(self):
        whatsapp = self.cleaned_data.get("whatsapp")
        if whatsapp and not re.match(r"^\+?\d{8,20}$", whatsapp):
            raise forms.ValidationError("WhatsApp deve ser válido.")
        return whatsapp

    def save(self, commit: bool = True) -> User:
        user = super().save(commit=False)
        user.cnpj = self.cleaned_data.get("cnpj")
        user.razao_social = self.cleaned_data.get("razao_social")
        user.nome_fantasia = self.cleaned_data.get("nome_fantasia")
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
            "cnpj",
            "razao_social",
            "nome_fantasia",
            "avatar",
            "contato",
            "biografia",
            "cover",
            "phone_number",
            "whatsapp",
            "birth_date",
            "redes_sociais",
            "organizacao",
            "nucleo",
            "area_atuacao",
            "descricao_atividade",
        )
        labels = {"contato": "Contato"}
        widgets = {
            "birth_date": forms.DateInput(format="%Y-%m-%d", attrs={"type": "date"})
        }

    def clean_cpf(self):
        cpf = self.cleaned_data.get("cpf")
        if not cpf:
            return cpf
        cpf_validator(cpf)
        _validate_cpf_reuse(self, cpf, exclude_pk=self.instance.pk)
        return cpf

    def clean_cnpj(self):
        cnpj = self.cleaned_data.get("cnpj")
        if not cnpj:
            return cnpj
        try:
            cnpj = validate_cnpj(cnpj)
        except DjangoValidationError as exc:
            raise forms.ValidationError(exc.messages)
        qs = User.objects.all()
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.filter(cnpj=cnpj).exists():
            raise forms.ValidationError(_("CNPJ já cadastrado."))
        return cnpj

    def clean(self):
        cleaned_data = super().clean()
        cpf_raw = (_get_field_value(self, "cpf") or "").strip()
        cnpj_raw = (_get_field_value(self, "cnpj") or "").strip()
        if not cpf_raw and not cnpj_raw:
            self.add_error("cpf", IDENTIFIER_REQUIRED_ERROR)
            self.add_error("cnpj", IDENTIFIER_REQUIRED_ERROR)
            raise forms.ValidationError(IDENTIFIER_REQUIRED_ERROR)
        return cleaned_data


class InformacoesPessoaisForm(forms.ModelForm):
    contato = forms.CharField(max_length=150, label="Contato")
    cpf = forms.CharField(max_length=14, required=False, label="CPF", validators=[cpf_validator])
    cnpj = forms.CharField(max_length=18, required=False, label="CNPJ")
    razao_social = forms.CharField(max_length=255, required=False, label="Razão social")
    nome_fantasia = forms.CharField(max_length=255, required=False, label="Nome fantasia")
    area_atuacao = forms.ChoiceField(
        choices=getattr(User, "AREA_ATUACAO_CHOICES", AREA_ATUACAO_CHOICES),
        required=False,
        label="Área de atuação",
    )
    descricao_atividade = forms.CharField(
        required=False,
        label="Descrição da atividade",
        widget=forms.Textarea(attrs={"rows": 3}),
    )
    facebook = forms.URLField(required=False, label=_("Facebook"), assume_scheme="https")
    twitter = forms.URLField(required=False, label=_("Twitter"), assume_scheme="https")
    instagram = forms.URLField(required=False, label=_("Instagram"), assume_scheme="https")
    linkedin = forms.URLField(required=False, label=_("LinkedIn"), assume_scheme="https")
    birth_date = forms.DateField(
        required=False,
        label="Data de nascimento",
        input_formats=["%Y-%m-%d"],
        widget=forms.DateInput(format="%Y-%m-%d", attrs={"type": "date"}),
    )

    class Meta:
        model = User
        fields = (
            "contato",
            "username",
            "email",
            "cpf",
            "cnpj",
            "razao_social",
            "nome_fantasia",
            "avatar",
            "cover",
            "biografia",
            "phone_number",
            "whatsapp",
            "birth_date",
            "endereco",
            "cidade",
            "estado",
            "cep",
            "area_atuacao",
            "descricao_atividade",
        )
        labels = {
            "avatar": _("Foto do perfil"),
            "cover": _("Imagem da capa"),
        }
        widgets = {
            "avatar": ProfileImageFileInput(
                button_label=_("Enviar foto"),
                empty_label=_("Nenhuma foto selecionada"),
            ),
            "cover": ProfileImageFileInput(
                button_label=_("Enviar imagem"),
                empty_label=_("Nenhuma imagem selecionada"),
            ),
        }

    field_order = (
        "username",
        "razao_social",
        "nome_fantasia",
        "cnpj",
        "area_atuacao",
        "descricao_atividade",
        "biografia",
        "contato",
        "cpf",
        "phone_number",
        "whatsapp",
        "birth_date",
        "email",
        "endereco",
        "cidade",
        "estado",
        "cep",
        "avatar",
        "cover",
        "facebook",
        "twitter",
        "instagram",
        "linkedin",
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.order_fields(self.field_order)
        if self.instance.pk:
            self.initial["contato"] = self.instance.contato
            self.initial["cpf"] = self.instance.cpf
            self.initial["cnpj"] = self.instance.cnpj
            self.initial["razao_social"] = self.instance.razao_social
            self.initial["nome_fantasia"] = self.instance.nome_fantasia
            self.initial["area_atuacao"] = self.instance.area_atuacao
            self.initial["descricao_atividade"] = self.instance.descricao_atividade
            self.initial["birth_date"] = self.instance.birth_date
            self.original_email = self.instance.email
        else:
            self.original_email = None
        redes = getattr(self.instance, "redes_sociais", None) or {}
        for field in ("facebook", "twitter", "instagram", "linkedin"):
            if redes.get(field):
                self.fields[field].initial = redes[field]

    def clean_cpf(self):
        cpf = self.cleaned_data.get("cpf")
        if not cpf:
            return cpf
        _validate_cpf_reuse(self, cpf, exclude_pk=self.instance.pk)
        return cpf

    def clean_cnpj(self):
        cnpj = self.cleaned_data.get("cnpj")
        if not cnpj:
            return cnpj
        try:
            cnpj = validate_cnpj(cnpj)
        except DjangoValidationError as exc:
            raise forms.ValidationError(exc.messages)
        if User.objects.exclude(pk=self.instance.pk).filter(cnpj=cnpj).exists():
            raise forms.ValidationError(_("CNPJ já cadastrado."))
        return cnpj

    def clean(self):
        cleaned_data = super().clean()
        cpf_raw = (_get_field_value(self, "cpf") or "").strip()
        cnpj_raw = (_get_field_value(self, "cnpj") or "").strip()
        if not cpf_raw and not cnpj_raw:
            self.add_error("cpf", IDENTIFIER_REQUIRED_ERROR)
            self.add_error("cnpj", IDENTIFIER_REQUIRED_ERROR)
            raise forms.ValidationError(IDENTIFIER_REQUIRED_ERROR)
        return cleaned_data

    def save(self, commit: bool = True) -> User:
        user = super().save(commit=False)
        user.contato = self.cleaned_data.get("contato", "")
        user.cpf = self.cleaned_data.get("cpf")
        user.cnpj = self.cleaned_data.get("cnpj")
        user.razao_social = self.cleaned_data.get("razao_social")
        user.nome_fantasia = self.cleaned_data.get("nome_fantasia")
        user.area_atuacao = self.cleaned_data.get("area_atuacao")
        user.descricao_atividade = self.cleaned_data.get("descricao_atividade")
        user.birth_date = self.cleaned_data.get("birth_date")
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
