from __future__ import annotations

from rest_framework.permissions import SAFE_METHODS, BasePermission
from rest_framework.exceptions import NotAuthenticated

from accounts.models import UserType


class IsFinanceiroOrAdmin(BasePermission):
    """Allow access only to financial staff or admins."""

    def has_permission(self, request, view) -> bool:  # type: ignore[override]
        if not request.user.is_authenticated:
            raise NotAuthenticated()
        permitido = {UserType.ADMIN}
        tipo_fin = getattr(UserType, "FINANCEIRO", None)
        if tipo_fin:
            permitido.add(tipo_fin)
        return request.user.user_type in permitido


class IsNotRoot(BasePermission):
    """Negates access for root users."""

    def has_permission(self, request, view) -> bool:  # type: ignore[override]
        if not request.user.is_authenticated:
            return True
        return request.user.user_type != UserType.ROOT


class IsCoordenador(BasePermission):
    """Permit coordinators to access their own nucleus resources."""

    def has_permission(self, request, view) -> bool:  # type: ignore[override]
        return request.user.is_authenticated and request.user.user_type == UserType.COORDENADOR


class IsAssociadoReadOnly(BasePermission):
    """Associados only view their own records."""

    def has_permission(self, request, view) -> bool:  # type: ignore[override]
        if not request.user.is_authenticated:
            return False
        if request.method in SAFE_METHODS:
            return request.user.user_type in {
                UserType.ASSOCIADO,
                UserType.NUCLEADO,
                UserType.COORDENADOR,
            }
        return False
