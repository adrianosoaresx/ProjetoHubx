from django import forms
from .models import Categoria, Topico, Resposta


class TopicoForm(forms.ModelForm):
    class Meta:
        model = Topico
        fields = ["categoria", "titulo", "conteudo"]
        widgets = {
            "categoria": forms.Select(attrs={"class": "form-control"}),
            "titulo": forms.TextInput(attrs={"class": "form-control"}),
            "conteudo": forms.Textarea(attrs={"class": "form-control", "rows": 4}),
        }


class RespostaForm(forms.ModelForm):
    class Meta:
        model = Resposta
        fields = ["conteudo"]
        widgets = {
            "conteudo": forms.Textarea(attrs={"class": "form-control", "rows": 4})
        }


class CategoriaForm(forms.ModelForm):
    class Meta:
        model = Categoria
        fields = ["nome", "descricao"]
        widgets = {
            "nome": forms.TextInput(attrs={"class": "form-control"}),
            "descricao": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
        }
