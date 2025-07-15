from typing import Tuple

from django import forms

from .models import Post


class PostForm(forms.ModelForm):
    destino = forms.ChoiceField(label="Visibilidade")

    class Meta:
        model = Post
        fields = ["conteudo", "image", "pdf"]
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
