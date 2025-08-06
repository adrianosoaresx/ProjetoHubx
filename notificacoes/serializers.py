from __future__ import annotations

from rest_framework import serializers

from .models import NotificationLog, NotificationTemplate, PushSubscription


class NotificationTemplateSerializer(serializers.ModelSerializer):
    class Meta:
        model = NotificationTemplate
        fields = ["id", "codigo", "assunto", "corpo", "canal", "ativo"]
class NotificationLogSerializer(serializers.ModelSerializer):
    template_codigo = serializers.CharField(source="template.codigo", read_only=True)
    template_assunto = serializers.CharField(source="template.assunto", read_only=True)
    template_corpo = serializers.CharField(source="template.corpo", read_only=True)

    class Meta:
        model = NotificationLog
        fields = [
            "id",
            "user",
            "template_codigo",
            "template_assunto",
            "template_corpo",
            "canal",
            "status",
            "data_envio",
            "erro",
            "destinatario",
        ]
        read_only_fields = [
            "id",
            "user",
            "template_codigo",
            "template_assunto",
            "template_corpo",
            "canal",
            "data_envio",
            "erro",
            "destinatario",
        ]


class PushSubscriptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = PushSubscription
        fields = ["token"]
