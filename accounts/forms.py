from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm
from .models import NotificationSettings, UserMedia, TokenAcesso
from nucleos.models import Nucleo

User = get_user_model()


class CustomUserCreationForm(UserCreationForm):
    """Simplified ``UserCreationForm`` that also includes ``email``."""

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("username", "email", "password1", "password2")


class InformacoesPessoaisForm(forms.ModelForm):
    nome = forms.CharField(max_length=150, label="Nome completo")

    class Meta:
        model = User
        fields = (
            "nome",
            "username",
            "email",
            "bio",
            "data_nascimento",
            "genero",
            "avatar",
            "telefone",
            "whatsapp",
            "endereco",
            "cidade",
            "estado",
            "cep",
            "idioma",
            "fuso_horario",
            "perfil_publico",
            "mostrar_email",
            "mostrar_telefone",
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


class TokenAcessoForm(forms.ModelForm):
    class Meta:
        model = TokenAcesso
        fields = ["tipo_destino", "nucleo_destino"]

    def __init__(self, *args, user=None, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)

        if user and user.tipo_id == User.Tipo.SUPERADMIN:
            self.fields["tipo_destino"].choices = [(TokenAcesso.Tipo.ADMIN, "admin")]
            self.fields.pop("nucleo_destino")
        elif user:
            self.fields["tipo_destino"].choices = [
                (TokenAcesso.Tipo.GERENTE, "gerente"),
                (TokenAcesso.Tipo.CLIENTE, "cliente"),
            ]
            qs = (
                user.organizacao.nucleos.all()
                if user.organizacao
                else Nucleo.objects.none()
            )
            self.fields["nucleo_destino"].queryset = qs

    def clean(self):
        cleaned = super().clean()
        if (
            self.user
            and self.user.tipo_id == User.Tipo.ADMIN
            and cleaned.get("tipo_destino")
            in {TokenAcesso.Tipo.GERENTE, TokenAcesso.Tipo.CLIENTE}
            and not cleaned.get("nucleo_destino")
        ):
            self.add_error("nucleo_destino", "Selecione um núcleo")
        return cleaned
