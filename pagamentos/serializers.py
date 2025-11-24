from __future__ import annotations

from decimal import Decimal

from rest_framework import serializers

from pagamentos.models import Transacao


class CheckoutSerializer(serializers.Serializer):
    organizacao_id = serializers.UUIDField(required=False, allow_null=True)
    valor = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=Decimal("0.50"))
    metodo = serializers.ChoiceField(choices=Transacao.Metodo.choices)
    email = serializers.EmailField()
    nome = serializers.CharField(max_length=120)
    documento = serializers.CharField(max_length=40)
    parcelas = serializers.IntegerField(required=False, min_value=1)
    token_cartao = serializers.CharField(required=False, allow_blank=True)
    vencimento = serializers.DateTimeField(required=False)


class CheckoutResponseSerializer(serializers.Serializer):
    transacao_id = serializers.IntegerField()
    status = serializers.ChoiceField(choices=Transacao.Status.choices)
    metodo = serializers.ChoiceField(choices=Transacao.Metodo.choices)
    external_id = serializers.CharField(required=False, allow_null=True)


class WebhookSerializer(serializers.Serializer):
    id = serializers.CharField(required=False)
    data = serializers.DictField(child=serializers.JSONField(), required=False)
