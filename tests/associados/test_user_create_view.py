from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from accounts.models import UserType
from organizacoes.factories import OrganizacaoFactory


class OrganizacaoUserCreateViewTests(TestCase):
    def setUp(self):
        self.organizacao = OrganizacaoFactory()
        self.admin = get_user_model().objects.create_user(
            email="admin@example.com",
            username="admin",
            password="Admin!123",
            user_type=UserType.ADMIN,
            organizacao=self.organizacao,
        )
        self.url = reverse("associados:associados_adicionar")

    def test_form_contains_hidden_next_with_back_href(self):
        self.client.force_login(self.admin)
        referer = "/associados/"
        response = self.client.get(self.url, HTTP_REFERER=referer)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["back_href"], referer)
        self.assertContains(response, f'name="next" value="{referer}"')

    def test_success_redirects_to_next_when_valid(self):
        self.client.force_login(self.admin)
        next_url = "/organizacoes/"
        response = self.client.post(
            self.url,
            {
                "username": "novo_associado",
                "email": "novo@example.com",
                "contato": "Novo Associado",
                "user_type": UserType.ASSOCIADO.value,
                "password1": "StrongPass!1",
                "password2": "StrongPass!1",
                "next": next_url,
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, next_url)
        self.assertTrue(
            get_user_model().objects.filter(email="novo@example.com").exists()
        )

    def test_invalid_next_falls_back_to_default_success(self):
        self.client.force_login(self.admin)
        response = self.client.post(
            self.url,
            {
                "username": "outro_associado",
                "email": "outro@example.com",
                "contato": "Outro Associado",
                "user_type": UserType.ASSOCIADO.value,
                "password1": "Another1!",
                "password2": "Another1!",
                "next": "http://example.com/externo",
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, "/associados/")
        self.assertTrue(
            get_user_model().objects.filter(email="outro@example.com").exists()
        )
