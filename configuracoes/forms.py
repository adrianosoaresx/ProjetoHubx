from django import forms
from configuracoes.models import ConfiguracaoConta


class ConfiguracaoContaForm(forms.ModelForm):
    class Meta:
        model = ConfiguracaoConta
        fields = (
            "receber_notificacoes_email",
            "receber_notificacoes_whatsapp",
            "tema_escuro",
        )
