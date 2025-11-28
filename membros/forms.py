from __future__ import annotations

from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

from accounts.models import UserType
from organizacoes.utils import validate_cnpj

User = get_user_model()


class OrganizacaoUserCreateForm(UserCreationForm):
    username = forms.CharField(
        label=_("Nome de usuário"),
        max_length=45,
        help_text=_("Máximo de 45 caracteres."),
    )
    contato = forms.CharField(
        label=_("Nome completo"),
        max_length=150,
        required=False,
    )
    email = forms.EmailField(label=_("E-mail"))
    user_type = forms.ChoiceField(label=_("Tipo de usuário"))
    razao_social = forms.CharField(
        label=_("Razão social"),
        max_length=255,
        required=False,
    )
    nome_fantasia = forms.CharField(
        label=_("Nome fantasia"),
        max_length=255,
        required=False,
    )
    cnpj = forms.CharField(label="CNPJ", max_length=18, required=False)
    cpf = forms.CharField(label="CPF", max_length=14, required=False)
    area_atuacao = forms.ChoiceField(
        label=_("Área de atuação"),
        choices=User.AREA_ATUACAO_CHOICES,
        required=False,
    )
    descricao_atividade = forms.CharField(
        label=_("Descrição da atividade"),
        widget=forms.Textarea,
        required=False,
    )
    phone_number = forms.CharField(
        label=_("Telefone"),
        max_length=20,
        required=False,
    )
    whatsapp = forms.CharField(
        label=_("WhatsApp"),
        max_length=20,
        required=False,
    )
    birth_date = forms.DateField(
        label=_("Data de nascimento"),
        required=False,
        widget=forms.DateInput(attrs={"type": "date"}),
    )

    class Meta(UserCreationForm.Meta):
        model = User
        fields = (
            "username",
            "email",
            "contato",
            "user_type",
            "razao_social",
            "nome_fantasia",
            "cnpj",
            "cpf",
            "area_atuacao",
            "descricao_atividade",
            "phone_number",
            "whatsapp",
            "birth_date",
        )

    def __init__(
        self,
        *args,
        allowed_user_types: list[str] | None = None,
        **kwargs,
    ):
        self.allowed_user_types = allowed_user_types or []
        super().__init__(*args, **kwargs)

        type_labels = {choice[0]: choice[1] for choice in UserType.choices}
        choices = [
            (value, type_labels[value])
            for value in self.allowed_user_types
            if value in type_labels
        ]
        self.fields["user_type"].choices = choices

        if len(choices) == 1:
            self.fields["user_type"].initial = choices[0][0]
            self.fields["user_type"].widget = forms.HiddenInput()

        # Ajusta labels para manter consistência visual
        self.fields["password1"].label = _("Senha")
        self.fields["password2"].label = _("Confirmar senha")

        # Remove textos de ajuda padronizados que não seguem o estilo do projeto
        self.fields["username"].help_text = ""
        self.fields["password1"].help_text = ""
        self.fields["password2"].help_text = ""

    def clean_user_type(self):
        user_type = self.cleaned_data.get("user_type")
        if user_type not in self.allowed_user_types:
            raise forms.ValidationError(_("Tipo de usuário inválido."))
        return user_type

    def clean_email(self):
        email = self.cleaned_data.get("email")
        if email and User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError(_("Este e-mail já está em uso."))
        return email

    def clean_username(self):
        username = self.cleaned_data.get("username", "").strip()
        if len(username) > self.fields["username"].max_length:
            raise forms.ValidationError(
                _("O nome de usuário deve ter no máximo %(limit)s caracteres."),
                params={"limit": self.fields["username"].max_length},
            )
        return username

    def clean_cnpj(self):
        cnpj = self.cleaned_data.get("cnpj")
        if not cnpj:
            return cnpj

        try:
            cnpj = validate_cnpj(cnpj)
        except ValidationError as exc:
            raise forms.ValidationError(exc.message)

        if User.objects.filter(cnpj=cnpj).exists():
            raise forms.ValidationError(_("Este CNPJ já está em uso."))

        return cnpj

    def save(self, commit: bool = True, *, organizacao) -> User:
        if organizacao is None:
            raise ValueError("Organização é obrigatória para criar o usuário.")

        user = super().save(commit=False)
        user.email = self.cleaned_data.get("email")
        user.contato = self.cleaned_data.get("contato")
        selected_type = self.cleaned_data.get("user_type")
        user.user_type = selected_type
        user.organizacao = organizacao
        user.is_associado = selected_type == UserType.ASSOCIADO.value
        user.razao_social = self.cleaned_data.get("razao_social")
        user.nome_fantasia = self.cleaned_data.get("nome_fantasia")
        user.cnpj = self.cleaned_data.get("cnpj")
        user.cpf = self.cleaned_data.get("cpf")
        user.area_atuacao = self.cleaned_data.get("area_atuacao")
        user.descricao_atividade = self.cleaned_data.get("descricao_atividade")
        user.phone_number = self.cleaned_data.get("phone_number")
        user.whatsapp = self.cleaned_data.get("whatsapp")
        user.birth_date = self.cleaned_data.get("birth_date")

        if commit:
            user.save()
        return user
