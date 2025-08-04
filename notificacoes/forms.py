from __future__ import annotations  # pragma: no cover

from django import forms

from .models import Frequencia, NotificationTemplate, UserNotificationPreference


class NotificationTemplateForm(forms.ModelForm):
    class Meta:
        model = NotificationTemplate
        fields = ["codigo", "assunto", "corpo", "canal", "ativo"]

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.fields["corpo"].widget.attrs.setdefault("rows", 4)
        if self.instance and self.instance.pk:
            self.fields["codigo"].widget.attrs["readonly"] = True


class UserNotificationPreferenceForm(forms.ModelForm):
    class Meta:
        model = UserNotificationPreference
        fields = [
            "email",
            "push",
            "whatsapp",
            "frequencia_email",
            "frequencia_whatsapp",
        ]

    def clean(self):
        dados = super().clean()
        if not dados.get("email") and dados.get("frequencia_email") != Frequencia.IMEDIATA:
            self.add_error(
                "frequencia_email",
                "Defina o canal de e-mail como ativo para escolher a frequência.",
            )
        if not dados.get("whatsapp") and dados.get("frequencia_whatsapp") != Frequencia.IMEDIATA:
            self.add_error(
                "frequencia_whatsapp",
                "Defina o canal WhatsApp como ativo para escolher a frequência.",
            )
        return dados
