from django import forms
from .models import ChatConversation, ChatMessage


class NovaConversaForm(forms.ModelForm):
    class Meta:
        model = ChatConversation
        fields = ["titulo", "slug", "tipo_conversa", "organizacao", "nucleo", "evento", "imagem"]


class NovaMensagemForm(forms.ModelForm):
    class Meta:
        model = ChatMessage
        fields = ["conteudo", "arquivo"]

    def clean(self):
        cleaned = super().clean()
        if not cleaned.get("conteudo") and not cleaned.get("arquivo"):
            raise forms.ValidationError("Informe texto ou arquivo")
        return cleaned
