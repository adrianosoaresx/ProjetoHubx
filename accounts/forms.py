
from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm
from .models import NotificationSettings

User = get_user_model()


class CustomUserCreationForm(UserCreationForm):
    """Simplified ``UserCreationForm`` that also includes ``email``."""

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("username", "email", "password1", "password2")


class InformacoesPessoaisForm(forms.ModelForm):
    nome = forms.CharField(max_length=150, label='Nome completo')

    class Meta:
        model = User
        fields = ('nome', 'username', 'email', 'bio', 'data_nascimento', 'genero', 'avatar')
        widgets = {
            'data_nascimento': forms.DateInput(attrs={'type': 'date'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            full = f"{self.instance.first_name} {self.instance.last_name}".strip()
            self.initial['nome'] = full

    def save(self, commit=True):
        user = super().save(commit=False)
        nome = self.cleaned_data.get('nome', '').strip()
        partes = nome.split()
        user.first_name = partes[0] if partes else ''
        user.last_name = ' '.join(partes[1:]) if len(partes) > 1 else ''
        if commit:
            user.save()
        return user


class ContatoForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ('email', 'telefone', 'whatsapp', 'endereco', 'cidade', 'estado', 'cep')


class RedesSociaisForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ('facebook', 'twitter', 'instagram', 'linkedin', 'website')


class ContaForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ('idioma', 'fuso_horario', 'perfil_publico', 'mostrar_email', 'mostrar_telefone')


class NotificacoesForm(forms.ModelForm):
    class Meta:
        model = NotificationSettings
        exclude = ('user', )
