from __future__ import annotations

from rest_framework import serializers

from .models import DashboardFilter, DashboardCustomMetric


class DashboardFilterSerializer(serializers.ModelSerializer):
    class Meta:
        model = DashboardFilter
        fields = ["id", "nome", "filtros", "publico", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]


class DashboardCustomMetricSerializer(serializers.ModelSerializer):
    class Meta:
        model = DashboardCustomMetric
        fields = [
            "id",
            "code",
            "nome",
            "descricao",
            "escopo",
            "query_spec",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]
