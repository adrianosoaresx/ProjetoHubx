from django import forms
from typing import Tuple

from .models import Post


class PostForm(forms.ModelForm):
    destino = forms.ChoiceField(label="Visibilidade")

    class Meta:
        model = Post
        fields = ["conteudo", "media"]
        widgets = {
            "conteudo": forms.Textarea(
                attrs={"class": "form-control", "rows": 4, "placeholder": "Compartilhe algo..."}
            ),
            "media": forms.ClearableFileInput(attrs={"class": "form-control"}),
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        choices: list[Tuple[str, str]] = [("publico", "Público")]
        if user:
            choices.extend([(str(n.id), n.nome) for n in user.nucleos.all()])
        self.fields["destino"].choices = choices

    def clean(self):
        cleaned_data = super().clean()
        conteudo = cleaned_data.get("conteudo")
        media = cleaned_data.get("media")
        if not conteudo and not media:
            raise forms.ValidationError("Informe um conteúdo ou selecione uma mídia.")
        return cleaned_data
