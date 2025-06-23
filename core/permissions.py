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
