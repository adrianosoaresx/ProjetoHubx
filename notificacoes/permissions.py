from __future__ import annotations

from rest_framework.permissions import BasePermission


class CanSendNotifications(BasePermission):
    def has_permission(self, request, view) -> bool:
        user = request.user
        return bool(user and (user.is_staff or user.has_perm("notificacoes.can_send_notifications")))
