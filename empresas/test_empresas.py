from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import Client, TestCase
from django.urls import reverse

from empresas.models import Empresa
from accounts.models import UserType


class EmpresaVisibilityTests(TestCase):
    def setUp(self):
        # Garante que os registros UserType necessários existem
        UserType.objects.get_or_create(descricao="root")
        UserType.objects.get_or_create(descricao="admin")
        UserType.objects.get_or_create(descricao="user")
        UserType.objects.get_or_create(descricao="client")
        UserType.objects.get_or_create(descricao="manager")  # Adicionado para evitar falhas

        # Executa o comando para gerar dados de teste
        call_command("generate_test_data")

        # Recria os usuários necessários para os testes
        self.User = get_user_model()
        self.root_user = self.User.objects.create_user(username="root", email="root@example.com", password="test123", tipo=UserType.objects.get(descricao="root"))
        self.admin_user = self.User.objects.create_user(username="admin", email="admin@example.com", password="test123", tipo=UserType.objects.get(descricao="admin"))
        self.client_user = self.User.objects.create_user(username="client", email="client@example.com", password="test123", tipo=UserType.objects.get(descricao="client"))
        self.manager_user = self.User.objects.create_user(username="manager", email="manager@example.com", password="test123", tipo=UserType.objects.get(descricao="manager"))

        self.client = Client()

    def test_root_is_denied(self):
        root_user = self.User.objects.get(username="root")
        self.client.force_login(root_user)
        response = self.client.get(reverse("empresas:lista"))
        self.assertEqual(response.status_code, 403)

    def test_org_user_sees_organization_companies(self):
        user = self.User.objects.exclude(is_superuser=True).first()
        expected = Empresa.objects.filter(usuario__organizacao=user.organizacao)  # Corrigido para usar 'organizacao'
        self.client.force_login(user)
        response = self.client.get(reverse("empresas:lista"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(set(response.context["empresas"]), set(expected))

    def test_create_empresa(self):
        user = self.User.objects.exclude(is_superuser=True).first()
        self.client.force_login(user)
        response = self.client.post(reverse("empresas:criar"), {
            "nome": "Nova Empresa",
            "descricao": "Descrição da nova empresa",
        })
        self.assertEqual(response.status_code, 201)
        self.assertTrue(Empresa.objects.filter(nome="Nova Empresa").exists())

    def test_edit_empresa(self):
        user = self.User.objects.exclude(is_superuser=True).first()
        empresa = Empresa.objects.first()
        self.client.force_login(user)
        response = self.client.post(reverse("empresas:editar", args=[empresa.id]), {
            "nome": "Empresa Editada",
            "descricao": empresa.descricao,
        })
        self.assertEqual(response.status_code, 200)
        empresa.refresh_from_db()
        self.assertEqual(empresa.nome, "Empresa Editada")

    def test_delete_empresa(self):
        user = self.User.objects.exclude(is_superuser=True).first()
        empresa = Empresa.objects.first()
        self.client.force_login(user)
        response = self.client.post(reverse("empresas:deletar", args=[empresa.id]))
        self.assertEqual(response.status_code, 204)
        self.assertFalse(Empresa.objects.filter(id=empresa.id).exists())

    def test_permission_denied_for_unauthorized_user(self):
        unauthorized_user = self.User.objects.create_user(username="unauthorized", email="unauthorized@example.com", password="test123")
        self.client.force_login(unauthorized_user)
        response = self.client.get(reverse("empresas:lista"))
        self.assertEqual(response.status_code, 403)

    def test_admin_can_view_all_companies(self):
        admin_user = self.User.objects.get(username="admin")
        self.client.force_login(admin_user)
        response = self.client.get(reverse("empresas:lista"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context["empresas"]), Empresa.objects.count())

    def test_client_can_manage_own_companies(self):
        client_user = self.User.objects.get(username="client")
        self.client.force_login(client_user)

        # Test create
        response = self.client.post(reverse("empresas:criar"), {
            "nome": "Empresa Cliente",
            "descricao": "Descrição da empresa do cliente",
        })
        self.assertEqual(response.status_code, 201)
        self.assertTrue(Empresa.objects.filter(nome="Empresa Cliente").exists())

        # Test edit
        empresa = Empresa.objects.filter(usuario=client_user).first()
        response = self.client.post(reverse("empresas:editar", args=[empresa.id]), {
            "nome": "Empresa Cliente Editada",
            "descricao": empresa.descricao,
        })
        self.assertEqual(response.status_code, 200)
        empresa.refresh_from_db()
        self.assertEqual(empresa.nome, "Empresa Cliente Editada")

        # Test delete
        response = self.client.post(reverse("empresas:deletar", args=[empresa.id]))
        self.assertEqual(response.status_code, 204)
        self.assertFalse(Empresa.objects.filter(id=empresa.id).exists())

    def test_root_is_denied_all_actions(self):
        root_user = self.User.objects.get(username="root")
        self.client.force_login(root_user)

        # Test view
        response = self.client.get(reverse("empresas:lista"))
        self.assertEqual(response.status_code, 403)

        # Test create
        response = self.client.post(reverse("empresas:criar"), {
            "nome": "Empresa Root",
            "descricao": "Descrição da empresa do root",
        })
        self.assertEqual(response.status_code, 403)

        # Test edit
        empresa = Empresa.objects.first()
        response = self.client.post(reverse("empresas:editar", args=[empresa.id]), {
            "nome": "Empresa Root Editada",
            "descricao": empresa.descricao,
        })
        self.assertEqual(response.status_code, 403)

        # Test delete
        response = self.client.post(reverse("empresas:deletar", args=[empresa.id]))
        self.assertEqual(response.status_code, 403)
