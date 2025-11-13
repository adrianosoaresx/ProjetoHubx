from django.test import TestCase
from django.urls import reverse

from accounts.factories import UserFactory
from accounts.models import UserType
from organizacoes.factories import OrganizacaoFactory


class AssociadoListViewTests(TestCase):
    def setUp(self):
        self.organizacao = OrganizacaoFactory()
        self.admin = UserFactory(
            user_type=UserType.ADMIN.value,
            organizacao=self.organizacao,
        )
        self.client.force_login(self.admin)
        self.list_url = reverse("associados:associados_lista")
        self.api_url = reverse("associados:associados_lista_api")

    def test_sem_nucleo_section_excludes_admin_and_operator(self):
        associado_sem_nucleo = UserFactory(
            username="associado-sem-nucleo",
            contato="Associado Sem Núcleo",
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
        page_users = list(response.context["associados_sem_nucleo_page"].object_list)
        self.assertIn(associado_sem_nucleo, page_users)
        self.assertNotIn(admin_sem_nucleo, page_users)
        self.assertNotIn(operador_sem_nucleo, page_users)
        self.assertEqual(response.context["associados_sem_nucleo_count"], 1)

        api_response = self.client.get(self.api_url, {"section": "sem_nucleo"})
        self.assertEqual(api_response.status_code, 200)
        data = api_response.json()
        html = data["html"]
        self.assertIn("Associado Sem Núcleo", html)
        self.assertNotIn("Admin Sem Núcleo", html)
        self.assertNotIn("Operador Sem Núcleo", html)
        self.assertEqual(data["count"], 1)
