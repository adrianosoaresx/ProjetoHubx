from django import forms
from .models import ChatMessage, ChatConversation

class NovaConversaForm(forms.ModelForm):
    class Meta:
        model = ChatConversation
        fields = ["titulo", "tipo_conversa", "organizacao", "nucleo", "evento", "imagem"]


class NovaMensagemForm(forms.ModelForm):
    class Meta:
        model = ChatMessage
        fields = ["conteudo", "arquivo"]
