from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from agenda.models import Evento
from empresas.models import Empresa
from nucleos.models import Nucleo
from organizacoes.models import Organizacao
from accounts.enums import TipoUsuario


class DashboardPermissionsTests(TestCase):
    def setUp(self):
        User = get_user_model()


        self.root_user = User.objects.create_user(
            username="rootuser",
            email="rootuser@example.com",
            password="pass",
            tipo_id=User.Tipo.SUPERADMIN,
        )
        self.admin_user = User.objects.create_user(
            username="adminuser",
            email="adminuser@example.com",
            password="pass",
            tipo_id=User.Tipo.ADMIN,
        )
        self.manager_user = User.objects.create_user(
            username="manageruser",
            email="manageruser@example.com",
            password="pass",
            tipo_id=User.Tipo.GERENTE,
        )
        self.client_user = User.objects.create_user(
            username="clientuser",
            email="clientuser@example.com",
            password="pass",
            tipo_id=User.Tipo.CLIENTE,
        )
        org = Organizacao.objects.create(nome="Org 1", cnpj="00.000.000/0001-00")
        self.admin_user.organization = org  # Corrigido para usar 'organization'
        self.admin_user.save()
        self.manager_user.organization = org  # Corrigido para usar 'organization'
        self.manager_user.save()
        Nucleo.objects.create(nome="Nucleo", organizacao=org)
        Empresa.objects.create(
            nome="Empresa",
            cnpj="00.000.000/0001-01",
            tipo="TI",
            municipio="City",
            estado="ST",
            usuario=self.client_user,
        )
        Evento.objects.create(
            titulo="Evento",
            organizacao=org,
            descricao="",
            data_hora=timezone.now(),
            duracao=timedelta(hours=1),
        )

    def assert_status(self, user, url_name, status):
        self.client.force_login(user)
        response = self.client.get(reverse(f"dashboard:{url_name}"))
        self.assertEqual(response.status_code, status)

    def test_root_access(self):
        self.assert_status(self.root_user, "root", 200)
        self.assert_status(self.root_user, "admin", 200)
        self.assert_status(self.root_user, "gerente", 200)
        self.assert_status(self.root_user, "cliente", 403)

    def test_admin_access(self):
        self.assert_status(self.admin_user, "root", 403)
        self.assert_status(self.admin_user, "admin", 200)
        self.assert_status(self.admin_user, "gerente", 200)
        self.assert_status(self.admin_user, "cliente", 403)

    def test_manager_access(self):
        self.assert_status(self.manager_user, "root", 403)
        self.assert_status(self.manager_user, "admin", 403)
        self.assert_status(self.manager_user, "gerente", 200)
        self.assert_status(self.manager_user, "cliente", 403)

    def test_client_access(self):
        self.assert_status(self.client_user, "root", 403)
        self.assert_status(self.client_user, "admin", 403)
        self.assert_status(self.client_user, "gerente", 403)
        self.assert_status(self.client_user, "cliente", 200)
