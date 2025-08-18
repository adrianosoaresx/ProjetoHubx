from __future__ import annotations

from rest_framework import serializers

from .models import DashboardFilter, MetricDefinition


class DashboardFilterSerializer(serializers.ModelSerializer):
    class Meta:
        model = DashboardFilter
        fields = ["id", "nome", "filtros", "publico", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]


class MetricDefinitionSerializer(serializers.ModelSerializer):
    class Meta:
        model = MetricDefinition
        fields = [
            "id",
            "code",
            "titulo",
            "descricao",
            "provider",
            "params",
            "publico",
            "ativo",
            "owner",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at", "owner"]
