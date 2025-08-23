from django import forms
from django.utils.translation import gettext_lazy as _
from django_select2 import forms as s2forms
import os

from .validators import validate_uploaded_file

from .models import (
    BriefingEvento,
    Evento,
    FeedbackNota,
    InscricaoEvento,
    MaterialDivulgacaoEvento,
    ParceriaEvento,
    Tarefa,
)


class TarefaForm(forms.ModelForm):
    class Meta:
        model = Tarefa
        fields = [
            "titulo",
            "descricao",
            "data_inicio",
            "data_fim",
            "responsavel",
            "status",
        ]
        widgets = {
            "data_inicio": forms.DateTimeInput(attrs={"type": "datetime-local"}),
            "data_fim": forms.DateTimeInput(attrs={"type": "datetime-local"}),
            "descricao": forms.Textarea(attrs={"rows": 3}),
        }


class EventoForm(forms.ModelForm):
    class Meta:
        model = Evento
        fields = [
            "titulo",
            "descricao",
            "data_inicio",
            "data_fim",
            "local",
            "cidade",
            "estado",
            "cep",
            "coordenador",
            "status",
            "publico_alvo",
            "numero_convidados",
            "numero_presentes",
            "participantes_maximo",
            "espera_habilitada",
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
            "valor_pago",
            "metodo_pagamento",
            "comprovante_pagamento",
            "observacao",
        ]

    def clean_valor_pago(self):
        valor = self.cleaned_data.get("valor_pago")
        if valor is not None and valor <= 0:
            raise forms.ValidationError(_("O valor pago deve ser positivo."))
        return valor

    def clean_comprovante_pagamento(self):
        arquivo = self.cleaned_data.get("comprovante_pagamento")
        if not arquivo:
            return arquivo
        validate_uploaded_file(arquivo)
        return arquivo


class FeedbackForm(forms.ModelForm):
    class Meta:
        model = FeedbackNota
        fields = ["nota", "comentario"]


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

    def clean_arquivo(self):
        arquivo = self.cleaned_data.get("arquivo")
        if not arquivo:
            return arquivo
        validate_uploaded_file(arquivo)
        return arquivo

    def clean_imagem_thumb(self):
        img = self.cleaned_data.get("imagem_thumb")
        if not img:
            return img
        ext = os.path.splitext(img.name)[1].lower()
        if ext not in {".jpg", ".jpeg", ".png"}:
            raise forms.ValidationError(_("Formato de imagem não permitido."))
        if img.size > 10 * 1024 * 1024:
            raise forms.ValidationError(_("Imagem excede o tamanho máximo de 10MB."))
        return img


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


class BriefingEventoCreateForm(BriefingEventoForm):
    """Formulário de criação que inclui o evento associado."""

    class Meta(BriefingEventoForm.Meta):
        fields = ["evento", *BriefingEventoForm.Meta.fields]


class ParceriaEventoForm(forms.ModelForm):
    class Meta:
        model = ParceriaEvento
        fields = [
            "evento",
            "nucleo",
            "empresa",
            "cnpj",
            "contato",
            "representante_legal",
            "data_inicio",
            "data_fim",
            "tipo_parceria",
            "descricao",
            "acordo",
        ]

    def clean_acordo(self):
        arquivo = self.cleaned_data.get("acordo")
        if not arquivo:
            return arquivo
        validate_uploaded_file(arquivo)
        return arquivo
