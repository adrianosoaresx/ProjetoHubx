from django import forms
from django.core.exceptions import ObjectDoesNotExist
from django.forms import ClearableFileInput
from django.utils.translation import gettext_lazy as _
from django_select2 import forms as s2forms
from validate_docbr import CNPJ

from nucleos.models import Nucleo

from .validators import validate_uploaded_file
from .models import Evento, FeedbackNota, InscricaoEvento, ParceriaEvento
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
            "nucleo",
            "numero_convidados",
            "participantes_maximo",
            "valor_ingresso",
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
            "avatar": ClearableFileInput(),
            "cover": ClearableFileInput(),
        }

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop("request", None)
        super().__init__(*args, **kwargs)

        nucleo_field = self.fields.get("nucleo")
        if nucleo_field:
            nucleo_field.required = False
            nucleo_field.empty_label = _("Selecione um núcleo")

            queryset = Nucleo.objects.none()
            organizacao = None

            if self.request:
                try:
                    organizacao = getattr(self.request.user, "organizacao", None)
                except ObjectDoesNotExist:
                    organizacao = None

            if not organizacao and self.instance and getattr(self.instance, "organizacao_id", None):
                organizacao = self.instance.organizacao

            if organizacao:
                queryset = Nucleo.objects.filter(organizacao=organizacao).order_by("nome")

            if self.instance and self.instance.nucleo:
                queryset = queryset | Nucleo.objects.filter(pk=self.instance.nucleo.pk)

            nucleo_field.queryset = queryset.distinct()

    def clean(self):
        cleaned_data = super().clean()
        publico_alvo = cleaned_data.get("publico_alvo")
        nucleo = cleaned_data.get("nucleo")

        if publico_alvo == 1:
            if not nucleo:
                self.add_error("nucleo", _("Selecione um núcleo para eventos destinados apenas ao núcleo."))
        else:
            cleaned_data["nucleo"] = None

        return cleaned_data


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
class ParceriaEventoForm(forms.ModelForm):
    class Meta:
        model = ParceriaEvento
        fields = [
            "evento",
            "nucleo",
            "cnpj",
            "contato",
            "representante_legal",
            "data_inicio",
            "data_fim",
            "tipo_parceria",
            "descricao",
            "acordo",
        ]

    def clean_cnpj(self):
        cnpj = self.cleaned_data.get("cnpj", "")
        if not cnpj.isdigit() or len(cnpj) != 14:
            raise forms.ValidationError(_("CNPJ deve conter 14 dígitos."))
        if not CNPJ().validate(cnpj):
            raise forms.ValidationError(_("CNPJ inválido."))
        return cnpj

    def clean_acordo(self):
        arquivo = self.cleaned_data.get("acordo")
        if not arquivo:
            return arquivo
        validate_uploaded_file(arquivo)
        return arquivo
