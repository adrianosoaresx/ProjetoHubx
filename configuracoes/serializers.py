from __future__ import annotations

from rest_framework import serializers

from .models import ConfiguracaoConta, ConfiguracaoContextual


class ConfiguracaoContaSerializer(serializers.ModelSerializer):
    class Meta:
        model = ConfiguracaoConta
        fields = [
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
        ]


class ConfiguracaoContextualSerializer(serializers.ModelSerializer):
    """Serializador para CRUD de ``ConfiguracaoContextual``."""

    class Meta:
        model = ConfiguracaoContextual
        fields = [
            "id",
            "escopo_tipo",
            "escopo_id",
            "frequencia_notificacoes_email",
            "frequencia_notificacoes_whatsapp",
            "receber_notificacoes_push",
            "frequencia_notificacoes_push",
            "idioma",
            "tema",
        ]
        read_only_fields = ["id"]
