from __future__ import annotations

from __future__ import annotations

from django import forms

from .models import CategoriaDiscussao, TopicoDiscussao, RespostaDiscussao


class CategoriaDiscussaoForm(forms.ModelForm):
    class Meta:
        model = CategoriaDiscussao
        fields = ["nome", "descricao", "organizacao", "nucleo", "evento", "icone"]


class TopicoDiscussaoForm(forms.ModelForm):
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
        ]

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
        fields = ["conteudo", "arquivo", "reply_to"]
