from django import forms
from .models import Categoria, Topico, Resposta


class TopicoForm(forms.ModelForm):
    class Meta:
        model = Topico
        fields = ["categoria", "titulo", "conteudo"]


class RespostaForm(forms.ModelForm):
    class Meta:
        model = Resposta
        fields = ["conteudo"]
        widgets = {"conteudo": forms.Textarea(attrs={"rows": 4})}


class CategoriaForm(forms.ModelForm):
    class Meta:
        model = Categoria
        fields = ["nome", "descricao"]
