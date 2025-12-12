from django.test import TestCase
from django.urls import reverse

from accounts.factories import UserFactory
from accounts.models import UserType
from organizacoes.factories import OrganizacaoFactory


class MembrosListViewTests(TestCase):
    def setUp(self):
        self.organizacao = OrganizacaoFactory()
        self.admin = UserFactory(
            user_type=UserType.ADMIN.value,
            organizacao=self.organizacao,
        )
        self.client.force_login(self.admin)
        self.list_url = reverse("membros:membros_lista")
        self.api_url = reverse("membros:membros_lista_api")

    def test_sem_nucleo_section_excludes_admin_and_operator(self):
        associado_sem_nucleo = UserFactory(
            username="associado-sem-nucleo",
            contato="Membro Sem Núcleo",
            organizacao=self.organizacao,
            is_associado=True,
            user_type=UserType.ASSOCIADO.value,
        )
        admin_sem_nucleo = UserFactory(
            username="admin-sem-nucleo",
            contato="Admin Sem Núcleo",
            organizacao=self.organizacao,
            is_associado=True,
            user_type=UserType.ADMIN.value,
        )
        operador_sem_nucleo = UserFactory(
            username="operador-sem-nucleo",
            contato="Operador Sem Núcleo",
            organizacao=self.organizacao,
            is_associado=True,
            user_type=UserType.OPERADOR.value,
        )

        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, 200)
        page_users = list(response.context["membros_sem_nucleo_page"].object_list)
        self.assertIn(associado_sem_nucleo, page_users)
        self.assertNotIn(admin_sem_nucleo, page_users)
        self.assertNotIn(operador_sem_nucleo, page_users)
        self.assertEqual(response.context["membros_sem_nucleo_count"], 1)

        api_response = self.client.get(self.api_url, {"section": "sem_nucleo"})
        self.assertEqual(api_response.status_code, 200)
        data = api_response.json()
        html = data["html"]
        self.assertIn("Membro Sem Núcleo", html)
        self.assertNotIn("Admin Sem Núcleo", html)
        self.assertNotIn("Operador Sem Núcleo", html)
        self.assertEqual(data["count"], 1)

    def test_api_keeps_promote_button_when_requested(self):
        UserFactory(
            username="associado-sem-nucleo",
            contato="Membro Sem Núcleo",
            organizacao=self.organizacao,
            is_associado=True,
            user_type=UserType.ASSOCIADO.value,
        )

        response = self.client.get(
            self.api_url,
            {"section": "sem_nucleo", "show_promote_button": "true"},
        )
        self.assertEqual(response.status_code, 200)
        html = response.json()["html"]
        self.assertIn("Promover", html)

    def test_leads_include_inactive_users_in_counts_and_carousel(self):
        lead_ativo = UserFactory(
            username="lead-ativo",
            contato="Lead Ativo",
            organizacao=self.organizacao,
            user_type=UserType.CONVIDADO.value,
            is_active=True,
        )
        lead_inativo = UserFactory(
            username="lead-inativo",
            contato="Lead Inativo",
            organizacao=self.organizacao,
            user_type=UserType.CONVIDADO.value,
            is_active=False,
        )
        UserFactory(
            username="lead-outra-org",
            contato="Lead Outra Org",
            organizacao=OrganizacaoFactory(),
            user_type=UserType.CONVIDADO.value,
            is_active=False,
        )

        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, 200)

        leads_page = response.context["membros_leads_page"].object_list
        self.assertIn(lead_ativo, leads_page)
        self.assertIn(lead_inativo, leads_page)
        self.assertEqual(response.context["membros_leads_count"], 2)
        self.assertEqual(response.context["total_leads"], 2)

        api_response = self.client.get(self.api_url, {"section": "leads"})
        self.assertEqual(api_response.status_code, 200)
        api_data = api_response.json()
        self.assertEqual(api_data["count"], 2)
        html = api_data["html"]
        self.assertIn("Lead Ativo", html)
        self.assertIn("Lead Inativo", html)
