from rest_framework import permissions

from accounts.models import UserType


class IsAdminOrCoordenadorOrReadOnly(permissions.IsAuthenticated):
    """Allow write actions only to admins, operators, or coordinators."""

    def has_permission(self, request, view) -> bool:  # type: ignore[override]
        if not super().has_permission(request, view):
            return False
        tipo_usuario = getattr(request.user, "get_tipo_usuario", None)
        if callable(tipo_usuario):  # pragma: no cover - defensive
            tipo_usuario = tipo_usuario()
        if not tipo_usuario:
            tipo_usuario = getattr(request.user, "user_type", None)

        if isinstance(tipo_usuario, UserType):
            tipo_usuario_valor = tipo_usuario.value
        else:
            tipo_usuario_valor = tipo_usuario

        if tipo_usuario_valor == UserType.ROOT.value:
            return False

        if request.method in permissions.SAFE_METHODS:
            return True

        admin_or_operador = {UserType.ADMIN.value, UserType.OPERADOR.value}
        allowed = admin_or_operador | {UserType.COORDENADOR.value}

        return tipo_usuario_valor in allowed
