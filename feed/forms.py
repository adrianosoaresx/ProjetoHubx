from django import forms
from .models import Post


class PostForm(forms.ModelForm):
    class Meta:
        model = Post
        fields = ["conteudo", "imagem", "visibilidade"]

    def clean(self):
        cleaned_data = super().clean()
        conteudo = cleaned_data.get("conteudo")
        imagem = cleaned_data.get("imagem")
        if not conteudo and not imagem:
            raise forms.ValidationError("Informe um conteúdo ou selecione uma imagem.")
        return cleaned_data
