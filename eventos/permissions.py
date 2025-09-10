from rest_framework import permissions

from accounts.models import UserType


class IsAdminOrCoordenadorOrReadOnly(permissions.IsAuthenticated):
    """Allow write actions only to admins or coordinators."""

    def has_permission(self, request, view) -> bool:  # type: ignore[override]
        if not super().has_permission(request, view):
            return False
        if request.method in permissions.SAFE_METHODS:
            return True
        return request.user.user_type in {
            UserType.ADMIN,
            UserType.COORDENADOR,
            UserType.ROOT,
        }
