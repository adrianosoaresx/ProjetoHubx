from __future__ import annotations

from django import forms
from django.utils.translation import gettext_lazy as _
from django_select2 import forms as s2forms

from .models import CategoriaDiscussao, Denuncia, RespostaDiscussao, Tag, TopicoDiscussao
from .validators import validate_attachment


class CategoriaDiscussaoForm(forms.ModelForm):
    class Meta:
        model = CategoriaDiscussao
        fields = ["nome", "descricao", "organizacao", "nucleo", "evento", "icone"]
        widgets = {
            "organizacao": forms.HiddenInput(),
            "nucleo": forms.HiddenInput(),
            "evento": forms.HiddenInput(),
        }


class TagForm(forms.ModelForm):
    class Meta:
        model = Tag
        fields = ["nome"]


class TopicoDiscussaoForm(forms.ModelForm):
    tags = forms.ModelMultipleChoiceField(
        queryset=Tag.objects.all(),
        required=False,
        widget=s2forms.Select2TagWidget,
    )

    class Meta:
        model = TopicoDiscussao
        fields = [
            "categoria",
            "titulo",
            "conteudo",
            "publico_alvo",
            "tags",
            "nucleo",
            "evento",
            "fechado",
        ]
        widgets = {
            "categoria": forms.HiddenInput(),
            "nucleo": forms.HiddenInput(),
            "evento": forms.HiddenInput(),
            "fechado": forms.HiddenInput(),
        }

    def clean_tags(self):
        tags = list(self.cleaned_data.get("tags", []))
        if hasattr(self.data, "getlist"):
            raw_values = self.data.getlist("tags")
        else:
            raw_values = self.data.get("tags", [])
            if isinstance(raw_values, str):
                raw_values = [raw_values]
        existing_ids = {str(tag.id) for tag in tags}
        for value in raw_values:
            if value and value not in existing_ids:
                tag, _ = Tag.objects.get_or_create(nome=value)
                tags.append(tag)
        return tags

    def clean(self):
        cleaned = super().clean()
        categoria = cleaned.get("categoria")
        titulo = cleaned.get("titulo")
        if categoria and titulo:
            qs = TopicoDiscussao.objects.filter(categoria=categoria, titulo=titulo)
            if self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                self.add_error("titulo", "Título duplicado na categoria.")
        nucleo = cleaned.get("nucleo")
        evento = cleaned.get("evento")
        if categoria:
            if categoria.nucleo and nucleo and nucleo != categoria.nucleo:
                self.add_error("nucleo", "Núcleo não corresponde à categoria.")
            if categoria.evento and evento and evento != categoria.evento:
                self.add_error("evento", "Evento não corresponde à categoria.")
        return cleaned


class RespostaDiscussaoForm(forms.ModelForm):
    class Meta:
        model = RespostaDiscussao
        fields = ["conteudo", "arquivo", "reply_to", "motivo_edicao"]
        widgets = {"motivo_edicao": forms.Textarea(attrs={"rows": 2})}

    def clean_arquivo(self):
        arquivo = self.cleaned_data.get("arquivo")
        if arquivo:
            validate_attachment(arquivo)
        return arquivo


class DenunciaForm(forms.ModelForm):
    class Meta:
        model = Denuncia
        fields = ["motivo"]
        widgets = {"motivo": forms.Textarea(attrs={"rows": 3})}
        labels = {"motivo": _("Motivo")}
