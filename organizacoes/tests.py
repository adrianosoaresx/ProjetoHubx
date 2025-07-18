from django.test import TestCase
from django.urls import reverse

from accounts.models import User, UserType
from .models import Organizacao


class OrganizacaoPermissionsTests(TestCase):
    def setUp(self):
        self.root_user = User.objects.create_user(
            username="rootuser", password="pass", user_type=UserType.ROOT
        )
        self.admin_user = User.objects.create_user(
            username="adminuser", password="pass", user_type=UserType.ADMIN
        )
        org = Organizacao.objects.create(nome="Org 1", cnpj="00.000.000/0001-00")
        self.admin_user.organizacao = org
        self.admin_user.save()

    def test_root_can_access_list(self):
        self.client.force_login(self.root_user)
        response = self.client.get(reverse("organizacoes:list"))
        self.assertEqual(response.status_code, 200)

    def test_admin_cannot_access_list(self):
        self.client.force_login(self.admin_user)
        response = self.client.get(reverse("organizacoes:list"))
        self.assertEqual(response.status_code, 403)
