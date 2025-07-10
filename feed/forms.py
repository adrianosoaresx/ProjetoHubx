from django import forms
from .models import Post


class PostForm(forms.ModelForm):
    class Meta:
        model = Post
        fields = ["conteudo", "media", "tipo_feed", "nucleo"]
        widgets = {
            "conteudo": forms.Textarea(
                attrs={"class": "form-control", "rows": 4, "placeholder": "Compartilhe algo..."}
            ),
            "media": forms.ClearableFileInput(
                attrs={"class": "form-control"}
            ),
            "tipo_feed": forms.Select(
                attrs={"class": "form-control"}
            ),
        }

    def clean(self):
        cleaned_data = super().clean()
        conteudo = cleaned_data.get("conteudo")
        media = cleaned_data.get("media")
        if not conteudo and not media:
            raise forms.ValidationError("Informe um conteúdo ou selecione uma mídia.")
        return cleaned_data
