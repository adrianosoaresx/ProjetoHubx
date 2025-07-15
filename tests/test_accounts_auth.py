from django.contrib.auth import get_user_model
from django.db import IntegrityError
from django.test import Client, TestCase
from django.urls import reverse

from organizacoes.models import Organizacao

User = get_user_model()


class AuthTests(TestCase):
    def setUp(self):
        self.client = Client()

    def test_email_login_success(self):
        org = Organizacao.objects.create(nome="Org", cnpj="00.000.000/0001-99")
        User.objects.create_user(
            email="alpha@example.com",
            username="alpha",
            password="pass",
            organization=org,
        )
        resp = self.client.post(
            reverse("accounts:login"),
            {"username": "alpha@example.com", "password": "pass"},
        )
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp.url, "/accounts/perfil/")

    def test_username_duplicates_different_org(self):
        org1 = Organizacao.objects.create(nome="Org1", cnpj="00.000.000/0001-00")
        org2 = Organizacao.objects.create(nome="Org2", cnpj="00.000.000/0002-00")
        User.objects.create_user(
            email="user1@example.com",
            username="dup",
            password="pass",
            organization=org1,
        )
        user = User.objects.create_user(
            email="user2@example.com",
            username="dup",
            password="pass",
            organization=org2,
        )
        self.assertEqual(user.username, "dup")

    def test_username_duplicate_same_org_fails(self):
        org = Organizacao.objects.create(nome="Org", cnpj="00.000.000/0001-00")
        User.objects.create_user(
            email="one@example.com",
            username="dup",
            password="pass",
            organization=org,
        )
        with self.assertRaises(IntegrityError):
            User.objects.create_user(
                email="two@example.com",
                username="dup",
                password="pass",
                organization=org,
            )

    def test_superuser_created_with_email(self):
        user = User.objects.create_superuser(
            email="admin@example.com",
            username="admin",
            password="pass",
        )
        self.assertTrue(user.is_superuser)
        self.assertEqual(user.email, "admin@example.com")
