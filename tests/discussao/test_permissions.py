from django.test import Client, TestCase
from django.urls import reverse

from accounts.models import User, UserType
from discussao.models import CategoriaDiscussao, TopicoDiscussao


class DiscussaoPermissionTests(TestCase):
    def setUp(self):
        self.client = Client()
        from organizacoes.models import Organizacao

        self.org = Organizacao.objects.create(nome="Org", cnpj="00.000.000/0001-99", slug="org")
        self.admin = User.objects.create_user(
            username="admin", email="a@a.com", password="pass", user_type=UserType.ADMIN, organizacao=self.org
        )
        self.user = User.objects.create_user(
            username="u", email="u@u.com", password="pass", user_type=UserType.NUCLEADO, organizacao=self.org
        )
        self.categoria = CategoriaDiscussao.objects.create(nome="Cat", organizacao=self.org)

    def test_admin_can_create_topico(self):
        self.client.force_login(self.admin)
        resp = self.client.post(
            reverse("discussao:topico_criar", args=[self.categoria.slug]),
            {"titulo": "t", "conteudo": "c", "categoria": self.categoria.id, "publico_alvo": 0},
        )
        self.assertEqual(resp.status_code, 302)
        self.assertTrue(TopicoDiscussao.objects.filter(titulo="t").exists())

    def test_common_cannot_create_topico_in_restricted_category(self):
        self.client.force_login(self.user)
        resp = self.client.post(
            reverse("discussao:topico_criar", args=[self.categoria.slug]),
            {"titulo": "x", "conteudo": "c", "categoria": self.categoria.id, "publico_alvo": 0},
        )
        self.assertEqual(resp.status_code, 403)
