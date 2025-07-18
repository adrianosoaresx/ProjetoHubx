from django import forms
from configuracoes.models import ConfiguracaoConta
import pytz

class ConfiguracaoContaForm(forms.ModelForm):
    class Meta:
        model = ConfiguracaoConta
        fields = (
            "idioma",
            "tema",
            "timezone",
            "notificacoes_email",
            "notificacoes_push",
            "privacidade_perfil",
        )

    def clean_timezone(self):
        timezone = self.cleaned_data.get("timezone")
        if timezone not in pytz.common_timezones:
            raise forms.ValidationError("Fuso horário inválido.")
        return timezone
