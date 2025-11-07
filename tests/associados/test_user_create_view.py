from django.contrib.auth import get_user_model
from django.template.loader import render_to_string
from django.test import RequestFactory, TestCase
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

    def test_admin_associado_can_access_create_view(self):
        self.admin.is_associado = True
        self.admin.save(update_fields=["is_associado"])

        self.client.force_login(self.admin)
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)

    def test_cancel_button_points_to_list_without_history(self):
        self.client.force_login(self.admin)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)

        cancel_config = response.context["cancel_component_config"]
        self.assertEqual(cancel_config["href"], "/associados/")
        self.assertEqual(cancel_config["fallback_href"], "/associados/")
        self.assertTrue(cancel_config["prevent_history"])


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


class HeroActionTemplateTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()

    def render_template(self, user):
        request = self.factory.get("/")
        request.user = user
        return render_to_string("associados/hero_action.html", request=request)

    def test_root_without_organizacao_does_not_render_cta(self):
        root_user = get_user_model().objects.create_user(
            email="root@example.com",
            username="root",
            password="Root!123",
            user_type=UserType.ROOT,
        )

        rendered = self.render_template(root_user)

        self.assertNotIn("Adicionar associado", rendered)

    def test_admin_with_organizacao_renders_cta(self):
        organizacao = OrganizacaoFactory()
        admin_user = get_user_model().objects.create_user(
            email="admin-template@example.com",
            username="admin-template",
            password="AdminTemp!123",
            user_type=UserType.ADMIN,
            organizacao=organizacao,
        )

        rendered = self.render_template(admin_user)

        self.assertIn("Adicionar associado", rendered)
