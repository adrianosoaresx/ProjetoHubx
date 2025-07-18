from __future__ import annotations

from django import forms
from django.contrib.auth import get_user_model

from .models import Comment, Like, Post

User = get_user_model()


class PostForm(forms.ModelForm):
    """Formulário para criação e edição de ``Post``."""

    tipo_feed = forms.ChoiceField(choices=Post.TIPO_FEED_CHOICES)

    class Meta:
        model = Post
        fields = ["tipo_feed", "conteudo", "image", "pdf", "nucleo", "evento"]
        widgets = {
            "conteudo": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 4,
                    "placeholder": "Compartilhe algo...",
                }
            ),
            "image": forms.ClearableFileInput(attrs={"class": "form-control"}),
            "pdf": forms.ClearableFileInput(attrs={"class": "form-control"}),
        }

    def __init__(self, *args, user: User | None = None, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        if user:
            self.user = user
            self.fields["nucleo"].queryset = user.nucleos.all()
            self.fields["evento"].queryset = user.eventos.all()
        else:
            self.user = None

    def clean(self):
        cleaned_data = super().clean()
        img = cleaned_data.get("image")
        pdf = cleaned_data.get("pdf")
        conteudo = cleaned_data.get("conteudo")

        if img and pdf:
            raise forms.ValidationError("Envie apenas imagem OU PDF, não ambos.")
        if not conteudo and not img and not pdf:
            raise forms.ValidationError("Informe um conteúdo ou selecione uma mídia.")

        tipo_feed = cleaned_data.get("tipo_feed")
        nucleo = cleaned_data.get("nucleo")
        evento = cleaned_data.get("evento")

        if tipo_feed == "nucleo" and not nucleo:
            self.add_error("nucleo", "Selecione o núcleo.")
        if tipo_feed == "nucleo" and self.user and nucleo and nucleo not in self.user.nucleos.all():
            self.add_error("nucleo", "Usuário não é membro do núcleo.")
        if tipo_feed == "evento" and not evento:
            self.add_error("evento", "Selecione o evento.")

        return cleaned_data


class CommentForm(forms.ModelForm):
    class Meta:
        model = Comment
        fields = ["texto", "reply_to"]
        widgets = {
            "texto": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 3,
                    "placeholder": "Escreva um comentário...",
                }
            ),
        }


class LikeForm(forms.ModelForm):
    class Meta:
        model = Like
        fields = []
