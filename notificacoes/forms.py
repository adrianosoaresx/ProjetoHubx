from __future__ import annotations

from django import forms

from .models import NotificationTemplate, UserNotificationPreference


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
        fields = ["email", "push", "whatsapp"]
