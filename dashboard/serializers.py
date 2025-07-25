from __future__ import annotations

from rest_framework import serializers

from .models import DashboardFilter


class DashboardFilterSerializer(serializers.ModelSerializer):
    class Meta:
        model = DashboardFilter
        fields = ["id", "nome", "filtros", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]
