from django import forms
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _
from django_select2 import forms as s2forms

from .models import ChatChannel, ChatMessage

User = get_user_model()


class NovaConversaForm(forms.ModelForm):
    contexto_tipo = forms.ChoiceField(
        choices=ChatChannel.CONTEXT_CHOICES,
        label=_("Tipo de contexto"),
    )
    contexto_id = forms.UUIDField(
        required=False,
        label=_("Contexto"),
        widget=s2forms.Select2Widget,
    )
    participants = forms.ModelMultipleChoiceField(
        queryset=User.objects.none(),
        widget=s2forms.Select2MultipleWidget,
        required=False,
        label=_("Participantes"),
    )
    descricao = forms.CharField(
        widget=forms.Textarea(attrs={"rows": 3}),
        required=False,
        label=_("Descrição"),
    )
    imagem = forms.ImageField(required=False, label=_("Imagem"))

    class Meta:
        model = ChatChannel
        fields = [
            "contexto_tipo",
            "contexto_id",
            "titulo",
            "descricao",
            "imagem",
        ]

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        qs = User.objects.exclude(id=user.id) if user else User.objects.all()
        self.fields["participants"].queryset = qs
        self.fields["titulo"].label = _("Nome da conversa")


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
