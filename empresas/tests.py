from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import Client, TestCase
from django.urls import reverse

from empresas.models import Empresa
from accounts.models import UserType


class EmpresaVisibilityTests(TestCase):
    def setUp(self):
        # Cria explicitamente os tipos de usuário necessários
        tipos = ["admin", "manager", "client", "root"]
        for idx, desc in enumerate(tipos, start=1):
            UserType.objects.get_or_create(id=idx, defaults={"descricao": desc})
        
        # Garante que o registro UserType com descrição 'root' existe
        UserType.objects.get_or_create(descricao="root")
        
        # Chama o comando para gerar os dados de teste
        call_command("generate_test_data")
        
        self.client = Client()
        self.User = get_user_model()

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
        unauthorized_user = self.User.objects.create_user(username="unauthorized", password="test123")
        self.client.force_login(unauthorized_user)
        response = self.client.get(reverse("empresas:lista"))
        self.assertEqual(response.status_code, 403)
