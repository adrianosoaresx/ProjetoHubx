from __future__ import annotations  # pragma: no cover

from django import forms

from .models import NotificationTemplate


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


