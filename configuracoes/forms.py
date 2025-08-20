from __future__ import annotations

from django import forms
from django.utils.translation import gettext_lazy as _

from configuracoes.models import ConfiguracaoConta, ConfiguracaoContextual


class ConfiguracaoContaForm(forms.ModelForm):
    """Formulário para atualização de preferências do usuário."""

    class Meta:
        model = ConfiguracaoConta
        fields = (
            "receber_notificacoes_email",
            "frequencia_notificacoes_email",
            "receber_notificacoes_whatsapp",
            "frequencia_notificacoes_whatsapp",
            "receber_notificacoes_push",
            "frequencia_notificacoes_push",
            "idioma",
            "tema",
            "hora_notificacao_diaria",
            "hora_notificacao_semanal",
            "dia_semana_notificacao",
        )
        widgets = {
            "receber_notificacoes_email": forms.CheckboxInput(),
            "receber_notificacoes_whatsapp": forms.CheckboxInput(),
            "receber_notificacoes_push": forms.CheckboxInput(),
            "frequencia_notificacoes_email": forms.Select(),
            "frequencia_notificacoes_whatsapp": forms.Select(),
            "frequencia_notificacoes_push": forms.Select(),
            "idioma": forms.Select(),
            "tema": forms.Select(),
            "hora_notificacao_diaria": forms.TimeInput(format="%H:%M", attrs={"type": "time"}),
            "hora_notificacao_semanal": forms.TimeInput(format="%H:%M", attrs={"type": "time"}),
            "dia_semana_notificacao": forms.Select(),
        }
        help_texts = {
            "frequencia_notificacoes_email": _(
                "Aplicável apenas se notificações por e-mail estiverem ativas."
            ),
            "frequencia_notificacoes_whatsapp": _(
                "Aplicável apenas se notificações por WhatsApp estiverem ativas."
            ),
            "frequencia_notificacoes_push": _(
                "Aplicável apenas se notificações push estiverem ativas."
            ),
            "hora_notificacao_diaria": _("Horário para envio das notificações diárias."),
            "hora_notificacao_semanal": _(
                "Horário para envio das notificações semanais."
            ),
            "dia_semana_notificacao": _("Dia da semana para notificações semanais."),
        }

    def clean(self) -> dict[str, object]:
        data = super().clean()
        if not data.get("receber_notificacoes_email"):
            data["frequencia_notificacoes_email"] = self.instance.frequencia_notificacoes_email
        if not data.get("receber_notificacoes_whatsapp"):
            data["frequencia_notificacoes_whatsapp"] = (
                self.instance.frequencia_notificacoes_whatsapp
            )
        if not data.get("receber_notificacoes_push"):
            data["frequencia_notificacoes_push"] = (
                self.instance.frequencia_notificacoes_push
            )

        freq_email = data.get("frequencia_notificacoes_email")
        freq_whats = data.get("frequencia_notificacoes_whatsapp")
        freq_push = data.get("frequencia_notificacoes_push")

        if (
            freq_email == "diaria"
            or freq_whats == "diaria"
            or freq_push == "diaria"
        ):
            if not data.get("hora_notificacao_diaria"):
                self.add_error(
                    "hora_notificacao_diaria", _("Obrigatório para frequência diária.")
                )
        if (
            freq_email == "semanal"
            or freq_whats == "semanal"
            or freq_push == "semanal"
        ):
            if not data.get("hora_notificacao_semanal"):
                self.add_error(
                    "hora_notificacao_semanal", _("Obrigatório para frequência semanal.")
                )
            if data.get("dia_semana_notificacao") is None:
                self.add_error(
                    "dia_semana_notificacao", _("Obrigatório para frequência semanal.")
                )
        return data


class ConfiguracaoContextualForm(forms.ModelForm):
    """Formulário simples para CRUD de ``ConfiguracaoContextual``."""

    class Meta:
        model = ConfiguracaoContextual
        fields = (
            "escopo_tipo",
            "escopo_id",
            "receber_notificacoes_email",
            "frequencia_notificacoes_email",
            "receber_notificacoes_whatsapp",
            "frequencia_notificacoes_whatsapp",
            "receber_notificacoes_push",
            "frequencia_notificacoes_push",
            "idioma",
            "tema",
        )
