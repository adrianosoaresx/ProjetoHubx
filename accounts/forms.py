from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserChangeForm, UserCreationForm
import re

from .models import NotificationSettings, UserMedia
from accounts.models import User

User = get_user_model()


class CustomUserCreationForm(UserCreationForm):
    """Formulário de criação de usuário usando email como login."""

    class Meta(UserCreationForm.Meta):
        model = User
        fields = (
            "email",
            "cpf",
            "avatar",
            "organizacao",
            "nucleo",
        )

    def clean_cpf(self):
        cpf = self.cleaned_data.get("cpf")
        if not re.match(r"^\d{11}$", cpf):
            raise forms.ValidationError("CPF deve conter 11 dígitos numéricos.")
        return cpf

    def clean_telefone(self):
        telefone = self.cleaned_data.get("telefone")
        if not re.match(r"^\+?\d{10,15}$", telefone):
            raise forms.ValidationError("Telefone deve ser válido.")
        return telefone


class CustomUserChangeForm(UserChangeForm):
    class Meta:
        model = User
        fields = (
            "email",
            "cpf",
            "avatar",
            "organizacao",
            "nucleo",
        )


class InformacoesPessoaisForm(forms.ModelForm):
    nome = forms.CharField(max_length=150, label="Nome completo")

    class Meta:
        model = User
        fields = (
            "nome",
            "username",
            "email",
            "avatar",
            "endereco",
            "cidade",
            "estado",
            "cep",
        )
        widgets = {
            "data_nascimento": forms.DateInput(attrs={"type": "date"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            full = f"{self.instance.first_name} {self.instance.last_name}".strip()
            self.initial["nome"] = full

    def save(self, commit=True):
        user = super().save(commit=False)
        nome = self.cleaned_data.get("nome", "").strip()
        partes = nome.split()
        user.first_name = partes[0] if partes else ""
        user.last_name = " ".join(partes[1:]) if len(partes) > 1 else ""
        if commit:
            user.save()
        return user


class RedesSociaisForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ("facebook", "twitter", "instagram", "linkedin", "website")


class NotificacoesForm(forms.ModelForm):
    class Meta:
        model = NotificationSettings
        exclude = ("user",)


class MediaForm(forms.ModelForm):
    tags_field = forms.CharField(
        required=False,
        help_text="Separe as tags por vírgula",
        label="Tags",
    )

    class Meta:
        model = UserMedia
        fields = ("file", "descricao", "tags_field")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            self.fields["tags_field"].initial = ", ".join(
                self.instance.tags.values_list("nome", flat=True)
            )

    def save(self, commit=True):
        instance = super().save(commit=False)
        if commit:
            instance.save()
        tags_names = [
            t.strip()
            for t in self.cleaned_data.get("tags_field", "").split(",")
            if t.strip()
        ]
        from .models import MediaTag

        tags = []
        for name in tags_names:
            tag, _ = MediaTag.objects.get_or_create(nome=name)
            tags.append(tag)
        if commit:
            instance.tags.set(tags)
            self.save_m2m()
        else:
            self._save_m2m = lambda: instance.tags.set(tags)
        return instance
