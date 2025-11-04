from django import forms
from django.core.exceptions import ObjectDoesNotExist
from django.forms import ClearableFileInput
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django_select2 import forms as s2forms
from nucleos.models import Nucleo

from .validators import validate_uploaded_file
from .models import Evento, FeedbackNota, InscricaoEvento


class PDFClearableFileInput(ClearableFileInput):
    template_name = "eventos/widgets/pdf_clearable_file_input.html"


class ComprovanteFileInput(ClearableFileInput):
    template_name = "eventos/widgets/comprovante_file_input.html"

    def __init__(self, *args, **kwargs):
        attrs = kwargs.setdefault("attrs", {})
        existing_classes = attrs.get("class", "")
        attrs["class"] = f"{existing_classes} sr-only".strip()
        super().__init__(*args, **kwargs)

    def get_context(self, name, value, attrs):
        attrs = (attrs or {}).copy()
        existing_classes = attrs.get("class", "")
        if "sr-only" not in existing_classes.split():
            attrs["class"] = f"{existing_classes} sr-only".strip()
        attrs["data-payment-proof-input"] = "true"
        context = super().get_context(name, value, attrs)
        initial_name = ""
        initial_url = ""
        if value:
            if hasattr(value, "name"):
                initial_name = value.name or ""
            else:
                initial_name = str(value)
            if hasattr(value, "url"):
                initial_url = getattr(value, "url", "") or ""
        context["widget"]["initial_name"] = initial_name
        context["widget"]["initial_url"] = initial_url
        return context


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
            "status",
            "publico_alvo",
            "nucleo",
            "participantes_maximo",
            "gratuito",
            "valor",
            "cronograma",
            "informacoes_adicionais",
            "briefing",
            "parcerias",
            "avatar",
            "cover",
        ]
        widgets = {
            "data_inicio": forms.DateTimeInput(attrs={"type": "datetime-local"}),
            "data_fim": forms.DateTimeInput(attrs={"type": "datetime-local"}),
            "descricao": forms.Textarea(attrs={"rows": 3}),
            "avatar": ClearableFileInput(),
            "cover": ClearableFileInput(),
            "briefing": PDFClearableFileInput(attrs={"accept": "application/pdf"}),
            "parcerias": PDFClearableFileInput(attrs={"accept": "application/pdf"}),
        }

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop("request", None)
        super().__init__(*args, **kwargs)

        if not self.is_bound:
            for field_name in ("data_inicio", "data_fim"):
                dt_value = getattr(self.instance, field_name, None)
                if dt_value:
                    if timezone.is_naive(dt_value):
                        local_dt = timezone.make_naive(dt_value, timezone.get_current_timezone())
                    else:
                        local_dt = timezone.localtime(dt_value)
                    self.initial[field_name] = local_dt.strftime("%Y-%m-%dT%H:%M")

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

        if "cover" in self.fields:
            self.fields["cover"].label = _("Capa")

        participantes_field = self.fields.get("participantes_maximo")
        if participantes_field:
            participantes_field.label = _("Participantes (lotação)")

        for field_name, help_text in (
            ("briefing", _("Envie o briefing em formato PDF (até 20 MB).")),
            ("parcerias", _("Envie os documentos de parcerias em PDF (até 20 MB).")),
        ):
            if field_name in self.fields:
                self.fields[field_name].help_text = help_text

    def clean(self):
        cleaned_data = super().clean()
        publico_alvo = cleaned_data.get("publico_alvo")
        nucleo = cleaned_data.get("nucleo")

        if publico_alvo == 1:
            if not nucleo:
                self.add_error("nucleo", _("Selecione um núcleo para eventos destinados apenas ao núcleo."))
        else:
            cleaned_data["nucleo"] = None

        participantes_maximo = cleaned_data.get("participantes_maximo")

        if cleaned_data.get("gratuito"):
            cleaned_data["valor"] = None

        return cleaned_data

    def _clean_pdf_file(self, field_name):
        arquivo = self.cleaned_data.get(field_name)
        if not arquivo:
            return arquivo
        validate_uploaded_file(arquivo)
        return arquivo

    def clean_briefing(self):
        return self._clean_pdf_file("briefing")

    def clean_parcerias(self):
        return self._clean_pdf_file("parcerias")


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
    def __init__(self, *args, evento=None, **kwargs):
        self.evento = evento
        super().__init__(*args, **kwargs)
        valor_field = self.fields.get("valor_pago")
        if valor_field:
            valor_inicial = self._get_evento_valor()
            if valor_inicial is None and self.instance and self.instance.valor_pago is not None:
                valor_inicial = self.instance.valor_pago
            if valor_inicial is not None:
                valor_field.initial = valor_inicial
            valor_field.disabled = True
            valor_field.widget.attrs.setdefault("readonly", "readonly")

        comprovante_field = self.fields.get("comprovante_pagamento")
        if comprovante_field:
            comprovante_field.label = _("Comprovante do pagamento")

    def _get_evento_valor(self):
        if self.evento is not None:
            return getattr(self.evento, "valor", None)
        if self.instance and getattr(self.instance, "evento_id", None):
            evento = getattr(self.instance, "evento", None)
            if evento is not None:
                return getattr(evento, "valor", None)
        return None

    class Meta:
        model = InscricaoEvento
        fields = [
            "valor_pago",
            "metodo_pagamento",
            "comprovante_pagamento",
            "observacao",
        ]
        widgets = {
            "comprovante_pagamento": ComprovanteFileInput(
                attrs={"accept": ".jpg,.jpeg,.png,.pdf"}
            ),
        }

    def clean_valor_pago(self):
        valor_evento = self._get_evento_valor()
        if valor_evento is not None:
            valor = valor_evento
        else:
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
    nota = forms.TypedChoiceField(
        choices=[(i, i) for i in range(1, 6)],
        coerce=int,
        empty_value=None,
        label=_("Nota"),
    )

    class Meta:
        model = FeedbackNota
        fields = ["nota", "comentario"]
        widgets = {
            "comentario": forms.Textarea(attrs={"rows": 4}),
        }

