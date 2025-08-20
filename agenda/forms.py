from django import forms
from django.utils.translation import gettext_lazy as _
from django_select2 import forms as s2forms
import os

from .models import (
    BriefingEvento,
    Evento,
    FeedbackNota,
    InscricaoEvento,
    MaterialDivulgacaoEvento,
    ParceriaEvento,
)


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
        ext = os.path.splitext(arquivo.name)[1].lower()
        if ext in {".jpg", ".jpeg", ".png"}:
            max_size = 10 * 1024 * 1024
        elif ext == ".pdf":
            max_size = 20 * 1024 * 1024
        else:
            raise forms.ValidationError(_("Formato de arquivo não permitido."))
        if arquivo.size > max_size:
            raise forms.ValidationError(_("Arquivo excede o tamanho máximo permitido."))
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
        ext = os.path.splitext(arquivo.name)[1].lower()
        if ext in {".jpg", ".jpeg", ".png"}:
            max_size = 10 * 1024 * 1024
        elif ext == ".pdf":
            max_size = 20 * 1024 * 1024
        else:
            raise forms.ValidationError(_("Formato de arquivo não permitido."))
        if arquivo.size > max_size:
            raise forms.ValidationError(_("Arquivo excede o tamanho máximo permitido."))
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
