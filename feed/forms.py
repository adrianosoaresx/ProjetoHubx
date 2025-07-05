from django import forms
from .models import Post


class PostForm(forms.ModelForm):
    class Meta:
        model = Post
        fields = ["conteudo", "imagem", "visibilidade"]
        widgets = {
            "conteudo": forms.Textarea(
                attrs={"class": "form-control", "rows": 4, "placeholder": "Compartilhe algo..."}
            ),
            "imagem": forms.ClearableFileInput(
                attrs={"class": "form-control"}
            ),
            "visibilidade": forms.Select(
                attrs={"class": "form-control"}
            ),
        }

    def clean(self):
        cleaned_data = super().clean()
        conteudo = cleaned_data.get("conteudo")
        imagem = cleaned_data.get("imagem")
        if not conteudo and not imagem:
            raise forms.ValidationError("Informe um conteúdo ou selecione uma imagem.")
        return cleaned_data
