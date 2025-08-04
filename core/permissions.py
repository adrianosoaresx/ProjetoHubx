from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import UserPassesTestMixin
from rest_framework.permissions import BasePermission

from accounts.models import UserType

User = get_user_model()


class SuperadminRequiredMixin(UserPassesTestMixin):
    """Permite acesso apenas a superadministradores."""

    def test_func(self):
        return self.request.user.user_type == UserType.ROOT


class AdminRequiredMixin(UserPassesTestMixin):
    """Permite acesso a superadministradores e administradores."""

    raise_exception = True

    def test_func(self):
        return self.request.user.user_type in {UserType.ROOT, UserType.ADMIN}


class GerenteRequiredMixin(UserPassesTestMixin):
    """Permite acesso a gerentes, administradores e superadmins."""

    def test_func(self):
        return self.request.user.user_type in {
            UserType.ROOT,
            UserType.ADMIN,
            UserType.COORDENADOR,
        }


class ClienteRequiredMixin(UserPassesTestMixin):
    """Permite acesso apenas a clientes."""

    def test_func(self):
        return self.request.user.user_type == UserType.CONVIDADO


class NoSuperadminMixin(UserPassesTestMixin):
    """Bloqueia acesso ao usuário root (SUPERADMIN)."""

    def test_func(self):
        user = self.request.user
        return hasattr(user, "user_type") and user.user_type != UserType.ROOT


def no_superadmin_required(view_func=None):
    """Decorator que nega acesso ao usuário root."""
    from functools import wraps

    from django.http import HttpResponseForbidden

    def decorator(func):
        @wraps(func)
        def _wrapped(request, *args, **kwargs):
            if request.user.user_type == UserType.ROOT:
                return HttpResponseForbidden()
            return func(request, *args, **kwargs)

        return _wrapped

    if view_func:
        return decorator(view_func)
    return decorator


class IsSameOrganization(BasePermission):
    """Allow access only to objects within the user's organization."""

    def has_object_permission(self, request, view, obj) -> bool:
        return getattr(obj, "organization_id", None) == getattr(request.user, "organization_id", None)


class ClienteGerenteRequiredMixin(UserPassesTestMixin):
    """Permite acesso a nucleados e coordenadores."""

    def test_func(self):
        return self.request.user.user_type in {UserType.NUCLEADO, UserType.COORDENADOR}


def pode_crud_empresa(user, empresa=None) -> bool:
    """
    Retorna True se o usuário puder criar/editar/excluir a empresa,
    conforme matriz de permissões (Root/Admin = read‑only).
    """
    if not user.is_authenticated or not getattr(user, "organizacao", None):
        return False
    if user.is_superuser or user.user_type == UserType.ROOT:
        return False
    if user.user_type == UserType.ADMIN:
        if empresa is None:
            return True
        return empresa.organizacao_id == user.organizacao_id
    if user.user_type in {UserType.COORDENADOR, UserType.NUCLEADO}:
        if empresa is None:
            return True
        return empresa.usuario_id == user.id
    return False


class IsRoot(BasePermission):
    """Permite acesso apenas a usuários root."""

    def has_permission(self, request, view):
        return request.user.get_tipo_usuario == UserType.ROOT.value


class IsAdmin(BasePermission):
    """Permite acesso a administradores da mesma organização."""

    def has_object_permission(self, request, view, obj):
        return request.user.get_tipo_usuario == UserType.ADMIN.value and request.user.organizacao == obj.organizacao


class IsCoordenador(BasePermission):
    """Permite acesso a coordenadores da mesma organização."""

    def has_object_permission(self, request, view, obj):
        return (
            request.user.get_tipo_usuario == UserType.COORDENADOR.value and request.user.organizacao == obj.organizacao
        )


class IsModeratorUser(BasePermission):
    """Permite acesso a usuários root ou admin."""

    def has_permission(self, request, view) -> bool:
        tipo = getattr(request.user, "get_tipo_usuario", None)
        return tipo in {UserType.ROOT.value, UserType.ADMIN.value}


class IsOrgAdminOrSuperuser(BasePermission):
    """Permite acesso ao superusuário ou admin da organização."""

    def has_permission(self, request, view) -> bool:
        return request.user.is_authenticated

    def has_object_permission(self, request, view, obj) -> bool:
        user = request.user
        if (
            user.is_superuser
            or getattr(user, "user_type", None) == UserType.ROOT.value
            or user.get_tipo_usuario == UserType.ROOT.value
        ):
            return True
        org_id = getattr(obj, "pk", None)
        if org_id is None:
            org_id = getattr(obj, "organizacao_id", None)
        return (
            user.get_tipo_usuario == UserType.ADMIN.value
            and getattr(user, "organizacao_id", None) == org_id
        )
