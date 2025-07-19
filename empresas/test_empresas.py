from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from accounts.models import UserType
from empresas.models import Empresa


class EmpresaVisibilityTests(TestCase):
    def setUp(self):
        UserType.objects.create(descricao="root")
        UserType.objects.create(descricao="admin")
        UserType.objects.create(descricao="user")
        UserType.objects.create(descricao="client")
        UserType.objects.create(descricao="manager")

        super().setUp()

        self.User = get_user_model()
        self.root_user, _ = self.User.objects.get_or_create(
            username="root", defaults={"password": "rootpass", "email": "root@example.com"}
        )
        self.admin_user, _ = self.User.objects.get_or_create(
            username="admin", defaults={"password": "adminpass", "email": "admin@example.com"}
        )
        self.client_user, _ = self.User.objects.get_or_create(
            username="client", defaults={"password": "clientpass", "email": "client@example.com"}
        )
        self.manager_user, _ = self.User.objects.get_or_create(
            username="manager", defaults={"password": "managerpass", "email": "manager@example.com"}
        )

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
                "razao_social": "Nova Empresa",
                "nome_fantasia": "Fantasia Nova",
                "cnpj": "12.345.678/0001-99",
                "ramo_atividade": "Tecnologia",
                "endereco": "Rua Nova, 123",
                "cidade": "São Paulo",
                "estado": "SP",
                "cep": "12345-678",
                "email_corporativo": "contato@nova.com",
                "telefone_corporativo": "123456789",
                "site": "http://nova.com",
                "rede_social": "http://twitter.com/nova",
                "logo": None,
                "banner": None,
            },
            **{"HTTP_HX_REQUEST": "true"}
        )
        self.assertEqual(response.status_code, 201)
        self.assertTrue(Empresa.objects.filter(razao_social="Nova Empresa").exists())

    def test_edit_empresa(self):
        user = self.User.objects.exclude(is_superuser=True).first()
        empresa = Empresa.objects.first()
        self.client.force_login(user)
        response = self.client.post(
            reverse("empresas:editar", args=[empresa.id]),
            {
                "razao_social": "Empresa Editada",
                "nome_fantasia": empresa.nome_fantasia,
                "cnpj": empresa.cnpj,
                "ramo_atividade": empresa.ramo_atividade,
                "endereco": empresa.endereco,
                "cidade": empresa.cidade,
                "estado": empresa.estado,
                "cep": empresa.cep,
                "email_corporativo": empresa.email_corporativo,
                "telefone_corporativo": empresa.telefone_corporativo,
                "site": empresa.site,
                "rede_social": empresa.rede_social,
                "logo": empresa.logo,
                "banner": empresa.banner,
            },
            **{"HTTP_HX_REQUEST": "true"}
        )
        self.assertEqual(response.status_code, 200)
        empresa.refresh_from_db()
        self.assertEqual(empresa.razao_social, "Empresa Editada")

    def test_delete_empresa(self):
        user = self.User.objects.exclude(is_superuser=True).first()
        empresa = Empresa.objects.first()
        self.client.force_login(user)
        response = self.client.post(reverse("empresas:remover", args=[empresa.id]), **{"HTTP_HX_REQUEST": "true"})
        self.assertEqual(response.status_code, 204)
        self.assertFalse(Empresa.objects.filter(id=empresa.id).exists())

    def test_permission_denied_for_unauthorized_user(self):
        unauthorized_user = self.User.objects.create_user(
            username="unauthorized", email="unauthorized@example.com", password="test123"
        )
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
        response = self.client.post(
            reverse("empresas:criar"),
            {
                "razao_social": "Empresa Cliente",
                "nome_fantasia": "Cliente Ltda",
                "cnpj": "23.456.789/0001-00",
                "ramo_atividade": "Serviços",
                "endereco": "Rua A, 1",
                "cidade": "Florianópolis",
                "estado": "SC",
                "cep": "88000-000",
                "email_corporativo": "cliente@example.com",
                "telefone_corporativo": "4899999000",
                "site": "http://cliente.com",
                "rede_social": "",
            },
        )
        self.assertEqual(response.status_code, 201)
        self.assertTrue(Empresa.objects.filter(razao_social="Empresa Cliente").exists())

        # Test edit
        empresa = Empresa.objects.filter(usuario=client_user).first()
        response = self.client.post(
            reverse("empresas:editar", args=[empresa.id]),
            {
                "razao_social": "Empresa Cliente Editada",
                "nome_fantasia": empresa.nome_fantasia,
                "cnpj": empresa.cnpj,
                "ramo_atividade": empresa.ramo_atividade,
                "endereco": empresa.endereco,
                "cidade": empresa.cidade,
                "estado": empresa.estado,
                "cep": empresa.cep,
                "email_corporativo": empresa.email_corporativo,
                "telefone_corporativo": empresa.telefone_corporativo,
                "site": empresa.site,
                "rede_social": empresa.rede_social,
            },
        )
        self.assertEqual(response.status_code, 200)
        empresa.refresh_from_db()
        self.assertEqual(empresa.razao_social, "Empresa Cliente Editada")

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
        response = self.client.post(
            reverse("empresas:criar"),
            {
                "razao_social": "Empresa Root",
                "nome_fantasia": "Root Ltda",
                "cnpj": "11.111.111/0001-11",
                "ramo_atividade": "TI",
                "endereco": "Rua X, 1",
                "cidade": "SP",
                "estado": "SP",
                "cep": "01000-000",
                "email_corporativo": "root@root.com",
                "telefone_corporativo": "000",
                "site": "",
                "rede_social": "",
            },
        )
        self.assertEqual(response.status_code, 403)

        # Test edit
        empresa = Empresa.objects.first()
        response = self.client.post(
            reverse("empresas:editar", args=[empresa.id]),
            {
                "razao_social": "Empresa Root Editada",
                "nome_fantasia": empresa.nome_fantasia,
                "cnpj": empresa.cnpj,
                "ramo_atividade": empresa.ramo_atividade,
                "endereco": empresa.endereco,
                "cidade": empresa.cidade,
                "estado": empresa.estado,
                "cep": empresa.cep,
                "email_corporativo": empresa.email_corporativo,
                "telefone_corporativo": empresa.telefone_corporativo,
                "site": empresa.site,
                "rede_social": empresa.rede_social,
            },
        )
        self.assertEqual(response.status_code, 403)

        # Test delete
        response = self.client.post(reverse("empresas:deletar", args=[empresa.id]))
        self.assertEqual(response.status_code, 403)

    def test_root_post_create(self):
        self.client.force_login(self.root_user)
        response = self.client.post(
            reverse("empresas:nova"),
            {
                "nome": "Empresa Root",
                "descricao": "Descrição da empresa do root",
            },
        )
        self.assertEqual(response.status_code, 403)

    def test_admin_post_create(self):
        self.client.force_login(self.admin_user)
        response = self.client.post(
            reverse("empresas:nova"),
            {
                "nome": "Empresa Admin",
                "descricao": "Descrição da empresa do admin",
            },
        )
        self.assertEqual(response.status_code, 403)

    def test_client_create_own(self):
        self.client.force_login(self.client_user)
        response = self.client.post(
            reverse("empresas:nova"),
            {
                "razao_social": "Empresa Cliente",
                "nome_fantasia": "Cliente LTDA",
                "cnpj": "66.666.666/0001-66",
                "ramo_atividade": "Serviços",
                "endereco": "Rua Z, 99",
                "cidade": "Rio",
                "estado": "RJ",
                "cep": "20000-000",
                "email_corporativo": "contato@cliente.com",
                "telefone_corporativo": "219999999",
                "site": "",
                "rede_social": "",
            },
            **{"HTTP_HX_REQUEST": "true"}
        )
        self.assertEqual(response.status_code, 201)
        self.assertTrue(Empresa.objects.filter(razao_social="Empresa Cliente").exists())

    def test_client_edit_foreign(self):
        empresa = Empresa.objects.exclude(usuario=self.client_user).first()
        self.client.force_login(self.client_user)
        response = self.client.post(
            reverse("empresas:editar", args=[empresa.id]),
            {
                "nome": "Tentativa de Edição",
            },
        )
        self.assertEqual(response.status_code, 403)

    def test_user_without_org_any(self):
        user_without_org = self.User.objects.create_user(
            username="semorg", email="semorg@example.com", password="test123"
        )
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
            endereco="Rua Teste, 123",
            cidade="São Paulo",
            estado="SP",
            cep="12345-678",
            logo=None,
            banner=None,
        )

    def test_empresa_fields(self):
        self.assertEqual(self.empresa.razao_social, "Empresa Teste")
        self.assertEqual(self.empresa.nome_fantasia, "Teste LTDA")
        self.assertEqual(self.empresa.ramo_atividade, "Tecnologia")
        self.assertEqual(self.empresa.cidade, "São Paulo")
        self.assertEqual(self.empresa.estado, "SP")
        self.assertEqual(self.empresa.endereco, "Rua Teste, 123")
        self.assertEqual(self.empresa.cep, "12345-678")
