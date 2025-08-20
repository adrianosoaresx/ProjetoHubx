from django import forms
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _
from django_select2 import forms as s2forms

from services.nucleos import user_belongs_to_nucleo

from .models import ChatChannel, ChatMessage

User = get_user_model()


class NovaConversaForm(forms.ModelForm):
    contexto_tipo = forms.ChoiceField(
        choices=ChatChannel.CONTEXT_CHOICES,
        label=_("Tipo de contexto"),
    )
    contexto_id = forms.CharField(
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
        self.user = user
        qs = User.objects.exclude(id=user.id) if user else User.objects.all()
        self.fields["participants"].queryset = qs
        self.fields["titulo"].label = _("Nome da conversa")

    def clean(self):
        cleaned = super().clean()
        contexto_tipo = cleaned.get("contexto_tipo")
        contexto_id = cleaned.get("contexto_id")
        participants = cleaned.get("participants") or []
        if contexto_tipo == "privado":
            if not contexto_id:
                self.add_error("contexto_id", _("Informe o núcleo"))
            else:
                nucleo_id = int(contexto_id)
                cleaned["contexto_id"] = nucleo_id
                users = [self.user] + list(participants)
                for u in users:
                    participa, info, suspenso = user_belongs_to_nucleo(u, nucleo_id)
                    if not (participa and info.endswith("ativo") and not suspenso):
                        raise forms.ValidationError(
                            _("Usuário não pertence ao núcleo informado")
                        )
        return cleaned


class NovaMensagemForm(forms.ModelForm):
    class Meta:
        model = ChatMessage
        fields = ["tipo", "conteudo", "arquivo", "reply_to"]
        widgets = {"reply_to": forms.HiddenInput()}

    def clean(self):
        cleaned = super().clean()
        tipo = cleaned.get("tipo")
        conteudo = cleaned.get("conteudo")
        arquivo = cleaned.get("arquivo")
        if tipo == "text" and not conteudo:
            raise forms.ValidationError("Informe o conteúdo de texto")
        if tipo in {"image", "video", "file"}:
            if not arquivo and not conteudo:
                raise forms.ValidationError("Envie o arquivo correspondente ou informe uma URL")
            if conteudo:
                from django.core.exceptions import ValidationError as URLValidationError
                from django.core.validators import URLValidator

                validator = URLValidator()
                try:
                    validator(conteudo)
                except URLValidationError as exc:
                    raise forms.ValidationError("URL de arquivo inválida") from exc
        return cleaned
