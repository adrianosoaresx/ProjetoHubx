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
            "data_inicio",
            "data_fim",
            "endereco",
            "cidade",
            "estado",
            "cep",
            "coordenador",
            "status",
            "publico_alvo",
            "numero_convidados",
            "numero_presentes",
            "valor_ingresso",
            "orcamento",
            "cronograma",
            "informacoes_adicionais",
            "contato_nome",
            "contato_email",
            "contato_whatsapp",
            "avatar",
            "cover",
        ]
        widgets = {
            "data_inicio": forms.DateTimeInput(attrs={"type": "datetime-local"}),
            "data_fim": forms.DateTimeInput(attrs={"type": "datetime-local"}),
            "descricao": forms.Textarea(attrs={"rows": 3}),
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
