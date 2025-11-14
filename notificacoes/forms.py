from __future__ import annotations  # pragma: no cover

from django import forms
from django.utils.translation import gettext_lazy as _

from .models import (
    Canal,
    Frequencia,
    NotificationStatus,
    NotificationTemplate,
    CANAL_LOG_CHOICES,
)


class NotificationTemplateForm(forms.ModelForm):
    class Meta:
        model = NotificationTemplate
        fields = ["codigo", "assunto", "corpo", "canal", "ativo"]

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.fields["corpo"].widget.attrs.setdefault("rows", 4)
        if self.instance and self.instance.pk:
            self.fields["codigo"].disabled = True

    def clean_codigo(self) -> str:
        if self.instance and self.instance.pk:
            return self.instance.codigo
        return self.cleaned_data["codigo"]


class HistoricoNotificacaoFilterForm(forms.Form):
    inicio = forms.DateField(
        label=_("Data inicial"),
        required=False,
        widget=forms.DateInput(attrs={"type": "date"}),
    )
    fim = forms.DateField(
        label=_("Data final"),
        required=False,
        widget=forms.DateInput(attrs={"type": "date"}),
    )
    canal = forms.ChoiceField(
        label=_("Canal"),
        required=False,
        choices=[("", _("Todos os canais"))] + list(Canal.choices),
    )
    frequencia = forms.ChoiceField(
        label=_("Frequência"),
        required=False,
        choices=[("", _("Todas as frequências"))] + list(Frequencia.choices),
    )
    ordenacao = forms.ChoiceField(
        label=_("Ordenação"),
        required=False,
        choices=[
            ("-enviado_em", _("Mais recentes primeiro")),
            ("enviado_em", _("Mais antigas primeiro")),
        ],
        initial="-enviado_em",
    )

    def clean_canal(self) -> str:
        canal = self.cleaned_data["canal"]
        return canal or ""

    def clean_frequencia(self) -> str:
        frequencia = self.cleaned_data["frequencia"]
        return frequencia or ""

    def clean_ordenacao(self) -> str:
        ordenacao = self.cleaned_data["ordenacao"]
        return ordenacao or "-enviado_em"


class NotificationLogFilterForm(forms.Form):
    inicio = forms.DateField(
        label=_("Data inicial"),
        required=False,
        widget=forms.DateInput(attrs={"type": "date"}),
    )
    fim = forms.DateField(
        label=_("Data final"),
        required=False,
        widget=forms.DateInput(attrs={"type": "date"}),
    )
    canal = forms.ChoiceField(
        label=_("Canal"),
        required=False,
        choices=[("", _("Todos os canais"))] + list(CANAL_LOG_CHOICES),
    )
    status = forms.ChoiceField(
        label=_("Status"),
        required=False,
        choices=[("", _("Todos os status"))] + list(NotificationStatus.choices),
    )
    template = forms.ModelChoiceField(
        label=_("Template"),
        required=False,
        queryset=NotificationTemplate.objects.none(),
        to_field_name="codigo",
    )

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.fields["template"].queryset = NotificationTemplate.objects.order_by("codigo")
        self.fields["template"].empty_label = _("Todos os templates")


class MetricsFilterForm(forms.Form):
    inicio = forms.DateField(
        label=_("Data inicial"),
        required=False,
        widget=forms.DateInput(attrs={"type": "date"}),
    )
    fim = forms.DateField(
        label=_("Data final"),
        required=False,
        widget=forms.DateInput(attrs={"type": "date"}),
    )
