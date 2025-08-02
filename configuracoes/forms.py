from __future__ import annotations

from django import forms
from django.utils.translation import gettext_lazy as _

from configuracoes.models import ConfiguracaoConta


class ConfiguracaoContaForm(forms.ModelForm):
    """Formulário para atualização de preferências do usuário."""

    class Meta:
        model = ConfiguracaoConta
        fields = (
            "receber_notificacoes_email",
            "frequencia_notificacoes_email",
            "receber_notificacoes_whatsapp",
            "frequencia_notificacoes_whatsapp",
            "idioma",
            "tema",
        )
        widgets = {
            "receber_notificacoes_email": forms.CheckboxInput(),
            "receber_notificacoes_whatsapp": forms.CheckboxInput(),
            "frequencia_notificacoes_email": forms.Select(),
            "frequencia_notificacoes_whatsapp": forms.Select(),
            "idioma": forms.Select(),
            "tema": forms.Select(),
        }
        help_texts = {
            "frequencia_notificacoes_email": _("Aplicável apenas se notificações por e-mail estiverem ativas."),
            "frequencia_notificacoes_whatsapp": _("Aplicável apenas se notificações por WhatsApp estiverem ativas."),
        }

    def clean(self) -> dict[str, object]:
        data = super().clean()
        if not data.get("receber_notificacoes_email"):
            data["frequencia_notificacoes_email"] = self.instance.frequencia_notificacoes_email
        if not data.get("receber_notificacoes_whatsapp"):
            data["frequencia_notificacoes_whatsapp"] = self.instance.frequencia_notificacoes_whatsapp
        return data
