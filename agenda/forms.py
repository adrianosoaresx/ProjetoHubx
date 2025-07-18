from django import forms
from django_select2 import forms as s2forms

from .models import Evento, InscricaoEvento, MaterialDivulgacaoEvento, BriefingEvento


class EventoForm(forms.ModelForm):
    class Meta:
        model = Evento
        fields = [
            "organizacao",
            "titulo",
            "descricao",
            "data_hora",
            "duracao",
            "link_inscricao",
            "briefing",
            "inscritos",
        ]
        widgets = {
            "data_hora": forms.DateTimeInput(attrs={"type": "datetime-local"}),
            "duracao": forms.TextInput(attrs={"placeholder": "HH:MM:SS"}),
            "inscritos": forms.SelectMultiple,
        }


class EventoWidget(s2forms.ModelSelect2Widget):
    search_fields = ["titulo__icontains"]


class EventoSearchForm(forms.Form):
    evento = forms.ModelChoiceField(
        queryset=Evento.objects.all(),
        required=False,
        label="",
        widget=EventoWidget(
            attrs={
                "data-placeholder": "Buscar eventos...",
                "data-minimum-input-length": 2,
            }
        ),
    )


class InscricaoEventoForm(forms.ModelForm):
    class Meta:
        model = InscricaoEvento
        fields = [
            "evento",
            "presente",
            "avaliacao",
            "valor_pago",
            "metodo_pagamento",
            "comprovante_pagamento",
            "observacao",
        ]


class MaterialDivulgacaoEventoForm(forms.ModelForm):
    class Meta:
        model = MaterialDivulgacaoEvento
        fields = [
            "evento",
            "titulo",
            "descricao",
            "tipo",
            "arquivo",
            "imagem_thumb",
            "tags",
        ]


class BriefingEventoForm(forms.ModelForm):
    class Meta:
        model = BriefingEvento
        fields = [
            "objetivos",
            "publico_alvo",
            "requisitos_tecnicos",
            "cronograma_resumido",
            "conteudo_programatico",
            "observacoes",
        ]
