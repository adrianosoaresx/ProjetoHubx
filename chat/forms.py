from django import forms
from django.contrib.auth import get_user_model

from .models import ChatConversation, ChatMessage

User = get_user_model()


class NovaConversaForm(forms.ModelForm):
    class Meta:
        model = ChatConversation
        fields = [
            "titulo",
            "tipo_conversa",
            "organizacao",
            "nucleo",
            "evento",
            "imagem",
        ]

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)
        if self.user:
            self.fields["organizacao"].queryset = self.user.organizacoes.all()
            self.fields["nucleo"].queryset = (
                self.user.nucleo_set.all() if hasattr(self.user, "nucleo_set") else User.objects.none()
            )
            self.fields["evento"].queryset = (
                self.user.eventos.all() if hasattr(self.user, "eventos") else User.objects.none()
            )


class NovaMensagemForm(forms.ModelForm):
    class Meta:
        model = ChatMessage
        fields = ["conteudo", "arquivo"]

    def clean(self):
        cleaned = super().clean()
        conteudo = cleaned.get("conteudo")
        arquivo = cleaned.get("arquivo")
        if not conteudo and not arquivo:
            raise forms.ValidationError("Informe um conteúdo ou anexe um arquivo.")
        return cleaned


class ConvidarParticipanteForm(forms.Form):
    usuario = forms.ModelChoiceField(queryset=User.objects.all())
