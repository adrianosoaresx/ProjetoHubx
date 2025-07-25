from django import forms

from .models import ChatConversation, ChatMessage


class NovaConversaForm(forms.ModelForm):
    class Meta:
        model = ChatConversation
        fields = ["titulo", "slug", "tipo_conversa", "organizacao", "nucleo", "evento", "imagem"]


class NovaMensagemForm(forms.ModelForm):
    class Meta:
        model = ChatMessage
        fields = ["tipo", "conteudo", "arquivo"]

    def clean(self):
        cleaned = super().clean()
        tipo = cleaned.get("tipo")
        conteudo = cleaned.get("conteudo")
        arquivo = cleaned.get("arquivo")
        if tipo == "text" and not conteudo:
            raise forms.ValidationError("Informe o conteúdo de texto")
        if tipo in {"image", "video", "file"} and not arquivo:
            raise forms.ValidationError("Envie o arquivo correspondente")
        return cleaned
