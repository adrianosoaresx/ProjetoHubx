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
            "receber_notificacoes_push",
            "frequencia_notificacoes_push",
            "idioma",
            "tema",
            "hora_notificacao_diaria",
            "hora_notificacao_semanal",
            "dia_semana_notificacao",
        ]

    def validate(self, attrs: dict) -> dict:
        """Valida combinações de frequência e horários de notificação.

        - Se um canal estiver desativado, mantém a frequência anterior.
        - Exige ``hora_notificacao_diaria`` quando alguma frequência for diária.
        - Exige ``hora_notificacao_semanal`` e ``dia_semana_notificacao`` quando
          alguma frequência for semanal.
        """

        instance = getattr(self, "instance", None)

        if attrs.get("receber_notificacoes_email") is False:
            attrs["frequencia_notificacoes_email"] = getattr(
                instance, "frequencia_notificacoes_email", "imediata"
            )
        if attrs.get("receber_notificacoes_whatsapp") is False:
            attrs["frequencia_notificacoes_whatsapp"] = getattr(
                instance, "frequencia_notificacoes_whatsapp", "imediata"
            )
        if attrs.get("receber_notificacoes_push") is False:
            attrs["frequencia_notificacoes_push"] = getattr(
                instance, "frequencia_notificacoes_push", "imediata"
            )

        freq_fields = [
            attrs.get("frequencia_notificacoes_email"),
            attrs.get("frequencia_notificacoes_whatsapp"),
            attrs.get("frequencia_notificacoes_push"),
        ]

        errors: dict[str, str] = {}

        if any(freq == "diaria" for freq in freq_fields):
            if "hora_notificacao_diaria" not in attrs:
                errors["hora_notificacao_diaria"] = "Obrigatório para frequência diária."

        if any(freq == "semanal" for freq in freq_fields):
            if "hora_notificacao_semanal" not in attrs:
                errors["hora_notificacao_semanal"] = "Obrigatório para frequência semanal."
            if "dia_semana_notificacao" not in attrs:
                errors["dia_semana_notificacao"] = "Obrigatório para frequência semanal."

        if errors:
            raise serializers.ValidationError(errors)

        return attrs


