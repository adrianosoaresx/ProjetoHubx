from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import Client, TestCase
from django.urls import reverse

from empresas.models import Empresa
from accounts.models import UserType


class EmpresaVisibilityTests(TestCase):
    def setUp(self):
        # Criação direta de instâncias de UserType
        UserType.objects.create(descricao="root")
        UserType.objects.create(descricao="admin")
        UserType.objects.create(descricao="user")
        UserType.objects.create(descricao="client")
        UserType.objects.create(descricao="manager")

        # Configuração adicional para os testes
        super().setUp()

        # Recria os usuários necessários para os testes
        self.User = get_user_model()
        self.root_user, _ = self.User.objects.get_or_create(username="root", defaults={"password": "rootpass", "email": "root@example.com"})
        self.admin_user, _ = self.User.objects.get_or_create(username="admin", defaults={"password": "adminpass", "email": "admin@example.com"})
        self.client_user, _ = self.User.objects.get_or_create(username="client", defaults={"password": "clientpass", "email": "client@example.com"})
        self.manager_user, _ = self.User.objects.get_or_create(username="manager", defaults={"password": "managerpass", "email": "manager@example.com"})

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
        response = self.client.post(
            reverse("empresas:criar"),
            {
                "nome": "Nova Empresa",
                "descricao": "Descrição da nova empresa",
            },
            **{"HTTP_HX_REQUEST": "true"}
        )
        self.assertEqual(response.status_code, 201)
        self.assertTrue(Empresa.objects.filter(nome="Nova Empresa").exists())

    def test_edit_empresa(self):
        user = self.User.objects.exclude(is_superuser=True).first()
        empresa = Empresa.objects.first()
        self.client.force_login(user)
        response = self.client.post(
            reverse("empresas:editar", args=[empresa.id]),
            {
                "nome": "Empresa Editada",
                "descricao": empresa.descricao,
            },
            **{"HTTP_HX_REQUEST": "true"}
        )
        self.assertEqual(response.status_code, 200)
        empresa.refresh_from_db()
        self.assertEqual(empresa.nome, "Empresa Editada")

    def test_delete_empresa(self):
        user = self.User.objects.exclude(is_superuser=True).first()
        empresa = Empresa.objects.first()
        self.client.force_login(user)
        response = self.client.post(
            reverse("empresas:remover", args=[empresa.id]),
            **{"HTTP_HX_REQUEST": "true"}
        )
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

    def test_root_post_create(self):
        self.client.force_login(self.root_user)
        response = self.client.post(reverse("empresas:nova"), {
            "nome": "Empresa Root",
            "descricao": "Descrição da empresa do root",
        })
        self.assertEqual(response.status_code, 403)

    def test_admin_post_create(self):
        self.client.force_login(self.admin_user)
        response = self.client.post(reverse("empresas:nova"), {
            "nome": "Empresa Admin",
            "descricao": "Descrição da empresa do admin",
        })
        self.assertEqual(response.status_code, 403)

    def test_client_create_own(self):
        self.client.force_login(self.client_user)
        response = self.client.post(reverse("empresas:nova"), {
            "nome": "Empresa Cliente",
            "descricao": "Descrição da empresa do cliente",
        }, **{"HTTP_HX_REQUEST": "true"})
        self.assertEqual(response.status_code, 201)
        self.assertTrue(Empresa.objects.filter(nome="Empresa Cliente").exists())

    def test_client_edit_foreign(self):
        empresa = Empresa.objects.exclude(usuario=self.client_user).first()
        self.client.force_login(self.client_user)
        response = self.client.post(reverse("empresas:editar", args=[empresa.id]), {
            "nome": "Tentativa de Edição",
        })
        self.assertEqual(response.status_code, 403)

    def test_user_without_org_any(self):
        user_without_org = self.User.objects.create_user(username="semorg", email="semorg@example.com", password="test123")
        self.client.force_login(user_without_org)
        response = self.client.get(reverse("empresas:lista"))
        self.assertEqual(response.status_code, 403)


class EmpresaModelTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="testuser",
            password="testpass",
            email="testuser@example.com",
        )
        self.empresa = Empresa.objects.create(
            usuario=self.user,
            cnpj="12.345.678/0001-99",
            razao_social="Empresa Teste",
            nome_fantasia="Teste LTDA",
            ramo_atividade="Tecnologia",
            cidade="São Paulo",
            estado="SP",
            endereco="Rua Teste, 123",
            banner=None,
            descricao="Uma empresa de teste",
            contato="(11) 99999-9999",
        )

    def test_empresa_fields(self):
        self.assertEqual(self.empresa.razao_social, "Empresa Teste")
        self.assertEqual(self.empresa.nome_fantasia, "Teste LTDA")
        self.assertEqual(self.empresa.ramo_atividade, "Tecnologia")
        self.assertEqual(self.empresa.cidade, "São Paulo")
        self.assertEqual(self.empresa.estado, "SP")
        self.assertEqual(self.empresa.endereco, "Rua Teste, 123")
        self.assertEqual(self.empresa.descricao, "Uma empresa de teste")
        self.assertEqual(self.empresa.contato, "(11) 99999-9999")
