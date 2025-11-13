from __future__ import annotations

from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm
from django.utils.translation import gettext_lazy as _

from accounts.models import UserType

User = get_user_model()


class OrganizacaoUserCreateForm(UserCreationForm):
    contato = forms.CharField(
        label=_("Nome completo"),
        max_length=150,
        required=False,
    )
    email = forms.EmailField(label=_("E-mail"))
    user_type = forms.ChoiceField(label=_("Tipo de usuário"))

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("username", "email", "contato")

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
        self.fields["username"].label = _("Nome de usuário")
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

        if commit:
            user.save()
        return user
