from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import Client, TestCase
from django.urls import reverse

from empresas.models import Empresa


class EmpresaVisibilityTests(TestCase):
    def setUp(self):
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
        expected = Empresa.objects.filter(usuario__organizacao=user.organizacao)
        self.client.force_login(user)
        response = self.client.get(reverse("empresas:lista"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(set(response.context["empresas"]), set(expected))
