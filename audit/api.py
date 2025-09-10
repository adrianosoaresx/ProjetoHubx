from __future__ import annotations

from rest_framework import permissions, serializers, viewsets

from accounts.models import UserType

from .models import AuditLog


class AuditLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = AuditLog
        fields = [
            "id",
            "user",
            "action",
            "object_type",
            "object_id",
            "ip_hash",
            "status",
            "metadata",
            "created_at",
        ]


class IsSuperAdmin(permissions.BasePermission):
    def has_permission(self, request, view) -> bool:
        return bool(request.user and request.user.is_authenticated and request.user.user_type == UserType.ROOT)


class AuditLogViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = AuditLog.objects.all()
    serializer_class = AuditLogSerializer
    permission_classes = [IsSuperAdmin]

    def get_queryset(self):  # type: ignore[override]
        qs = super().get_queryset()
        user_id = self.request.query_params.get("user_id")
        action = self.request.query_params.get("action")
        date_from = self.request.query_params.get("date_from")
        date_to = self.request.query_params.get("date_to")
        if user_id:
            qs = qs.filter(user_id=user_id)
        if action:
            qs = qs.filter(action=action)
        if date_from:
            qs = qs.filter(created_at__date__gte=date_from)
        if date_to:
            qs = qs.filter(created_at__date__lte=date_to)
        return qs
