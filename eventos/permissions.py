from rest_framework import permissions

from accounts.models import UserType


class IsAdminOrCoordenadorOrReadOnly(permissions.IsAuthenticated):
    """Allow write actions only to admins or coordinators."""

    def has_permission(self, request, view) -> bool:  # type: ignore[override]
        if not super().has_permission(request, view):
            return False
        if request.method in permissions.SAFE_METHODS:
            return True
        tipo_usuario = getattr(request.user, "get_tipo_usuario", None)
        if callable(tipo_usuario):  # pragma: no cover - defensive
            tipo_usuario = tipo_usuario()
        if not tipo_usuario:
            tipo_usuario = getattr(request.user, "user_type", None)
        return tipo_usuario in {
            UserType.ADMIN.value,
            UserType.COORDENADOR.value,
            UserType.OPERADOR.value,
            UserType.ROOT.value,
            UserType.ADMIN,
            UserType.COORDENADOR,
            UserType.OPERADOR,
            UserType.ROOT,
        }
