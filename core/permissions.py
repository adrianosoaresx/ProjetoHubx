from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import UserPassesTestMixin

User = get_user_model()

class SuperadminRequiredMixin(UserPassesTestMixin):
    """Permite acesso apenas a superadministradores."""

    def test_func(self):
        return self.request.user.tipo_id == User.Tipo.SUPERADMIN

class AdminRequiredMixin(UserPassesTestMixin):
    """Permite acesso a superadministradores e administradores."""

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
        return self.request.user.tipo_id != User.Tipo.SUPERADMIN


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
