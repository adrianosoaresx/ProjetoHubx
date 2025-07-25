from __future__ import annotations

from rest_framework import serializers

from .models import ConfiguracaoConta


class ConfiguracaoContaSerializer(serializers.ModelSerializer):
    class Meta:
        model = ConfiguracaoConta
        fields = [
            "receber_notificacoes_email",
            "frequencia_notificacoes_email",
            "receber_notificacoes_whatsapp",
            "frequencia_notificacoes_whatsapp",
            "idioma",
            "tema",
        ]
