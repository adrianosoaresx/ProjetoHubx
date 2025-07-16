from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import UserPassesTestMixin
from rest_framework.permissions import BasePermission

User = get_user_model()


class SuperadminRequiredMixin(UserPassesTestMixin):
    """Permite acesso apenas a superadministradores."""

    def test_func(self):
        return self.request.user.tipo_id == User.Tipo.SUPERADMIN


class AdminRequiredMixin(UserPassesTestMixin):
    """Permite acesso a superadministradores e administradores."""

    raise_exception = True

    def test_func(self):
        return self.request.user.tipo_id in {User.Tipo.SUPERADMIN, User.Tipo.ADMIN}


class GerenteRequiredMixin(UserPassesTestMixin):
    """Permite acesso a gerentes, administradores e superadmins."""

    def test_func(self):
        return self.request.user.tipo_id in {
            User.Tipo.SUPERADMIN,
            User.Tipo.ADMIN,
            User.Tipo.GERENTE,
        }


class ClienteRequiredMixin(UserPassesTestMixin):
    """Permite acesso apenas a clientes."""

    def test_func(self):
        return self.request.user.tipo_id == User.Tipo.CLIENTE


class NoSuperadminMixin(UserPassesTestMixin):
    """Bloqueia acesso ao usuário root (SUPERADMIN)."""

    def test_func(self):
        user = self.request.user
        return hasattr(user, "tipo_id") and user.tipo_id != User.Tipo.SUPERADMIN


def no_superadmin_required(view_func=None):
    """Decorator que nega acesso ao usuário root."""
    from functools import wraps

    from django.http import HttpResponseForbidden

    def decorator(func):
        @wraps(func)
        def _wrapped(request, *args, **kwargs):
            if request.user.tipo_id == User.Tipo.SUPERADMIN:
                return HttpResponseForbidden()
            return func(request, *args, **kwargs)

        return _wrapped

    if view_func:
        return decorator(view_func)
    return decorator


class IsSameOrganization(BasePermission):
    """Allow access only to objects within the user's organization."""

    def has_object_permission(self, request, view, obj) -> bool:
        return getattr(obj, "organization_id", None) == getattr(
            request.user, "organization_id", None
        )


class ClienteGerenteRequiredMixin(UserPassesTestMixin):
    """Permite acesso a clientes e gerentes."""

    def test_func(self):
        return self.request.user.tipo_id in {User.Tipo.CLIENTE, User.Tipo.GERENTE}


def pode_crud_empresa(user, empresa=None) -> bool:
    """
    Retorna True se o usuário puder criar/editar/excluir a empresa,
    conforme matriz de permissões (Root/Admin = read‑only).
    """
    if not user.is_authenticated or not user.organizacao:
        return False
    if user.is_superuser or user.tipo.descricao == "admin":
        return False
    # client ou manager:
    return empresa is None or empresa.usuario_id == user.id
