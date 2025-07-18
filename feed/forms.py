from typing import Tuple

from django import forms

from .models import Post, Comment, Like


class PostForm(forms.ModelForm):
    destino = forms.ChoiceField(label="Visibilidade")
    tipo_feed = forms.ChoiceField(
        label="Tipo de Feed",
        choices=Post.TIPO_FEED_CHOICES,
        widget=forms.Select(attrs={"class": "form-control"}),
    )

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

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        choices: list[Tuple[str, str]] = [("publico", "Público")]
        if user:
            choices.extend([(str(n.id), n.nome) for n in user.nucleos.all()])
            self.fields["nucleo"].queryset = user.nucleos.all()
            self.fields["evento"].queryset = user.eventos.all()
        self.fields["destino"].choices = choices

    def clean(self):
        cleaned_data = super().clean()
        img = cleaned_data.get("image")
        pdf = cleaned_data.get("pdf")
        conteudo = cleaned_data.get("conteudo")

        if img and pdf:
            raise forms.ValidationError("Envie apenas imagem OU PDF, não ambos.")
        if not conteudo and not img and not pdf:
            raise forms.ValidationError("Informe um conteúdo ou selecione uma mídia.")

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
