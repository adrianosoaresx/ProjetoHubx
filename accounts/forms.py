import json
import re

from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserChangeForm, UserCreationForm

from .models import NotificationSettings, UserMedia

User = get_user_model()


class CustomUserCreationForm(UserCreationForm):
    """Formulário de criação de usuário usando email como login."""

    class Meta(UserCreationForm.Meta):
        model = User
        fields = (
            "email",
            "cpf",
            "avatar",
            "nome_completo",
            "biografia",
            "cover",
            "fone",
            "whatsapp",
            "redes_sociais",
            "organizacao",
            "nucleo",
        )

    def clean_cpf(self):
        cpf = self.cleaned_data.get("cpf")
        if not re.match(r"^\d{11}$", cpf):
            raise forms.ValidationError("CPF deve conter 11 dígitos numéricos.")
        return cpf

    def clean_fone(self):
        fone = self.cleaned_data.get("fone")
        if fone and not re.match(r"^\+?\d{8,20}$", fone):
            raise forms.ValidationError("Telefone deve ser válido.")
        return fone

    def clean_whatsapp(self):
        whatsapp = self.cleaned_data.get("whatsapp")
        if whatsapp and not re.match(r"^\+?\d{8,20}$", whatsapp):
            raise forms.ValidationError("WhatsApp deve ser válido.")
        return whatsapp


class CustomUserChangeForm(UserChangeForm):
    class Meta:
        model = User
        fields = (
            "email",
            "cpf",
            "avatar",
            "nome_completo",
            "biografia",
            "cover",
            "fone",
            "whatsapp",
            "redes_sociais",
            "organizacao",
            "nucleo",
        )


class InformacoesPessoaisForm(forms.ModelForm):
    nome_completo = forms.CharField(max_length=255, label="Nome completo")

    class Meta:
        model = User
        fields = (
            "nome_completo",
            "username",
            "email",
            "avatar",
            "cover",
            "biografia",
            "fone",
            "whatsapp",
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
            self.initial["nome_completo"] = self.instance.nome_completo

    def save(self, commit=True):
        user = super().save(commit=False)
        user.nome_completo = self.cleaned_data.get("nome_completo", "")
        if commit:
            user.save()
        return user


class RedesSociaisForm(forms.ModelForm):
    redes_sociais = forms.JSONField(
        required=False,
        widget=forms.Textarea(attrs={"rows": 3}),
        label="Redes sociais (JSON)",
    )

    class Meta:
        model = User
        fields = ("redes_sociais",)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.redes_sociais:
            self.initial["redes_sociais"] = json.dumps(self.instance.redes_sociais, ensure_ascii=False, indent=2)

    def clean_redes_sociais(self):
        data = self.cleaned_data.get("redes_sociais") or {}
        if isinstance(data, str):
            try:
                data = json.loads(data)
            except json.JSONDecodeError as exc:
                raise forms.ValidationError("JSON inválido") from exc
        return data


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
            self.fields["tags_field"].initial = ", ".join(self.instance.tags.values_list("nome", flat=True))

    def save(self, commit=True):
        instance = super().save(commit=False)
        if commit:
            instance.save()
        tags_names = [t.strip() for t in self.cleaned_data.get("tags_field", "").split(",") if t.strip()]
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
