from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APITestCase
from validate_docbr import CNPJ

from accounts.models import UserType
from empresas.models import Empresa, FavoritoEmpresa
from organizacoes.factories import OrganizacaoFactory


class FavoritoAPITestCase(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.org1 = OrganizacaoFactory()
        cls.org2 = OrganizacaoFactory()
        User = get_user_model()
        cls.user1 = User.objects.create_user(
            email="u1@example.com",
            username="u1",
            password="pass",
            user_type=UserType.COORDENADOR,
            organizacao=cls.org1,
        )
        cls.user2 = User.objects.create_user(
            email="u2@example.com",
            username="u2",
            password="pass",
            user_type=UserType.COORDENADOR,
            organizacao=cls.org2,
        )
        cls.empresa = Empresa.objects.create(
            usuario=cls.user1,
            organizacao=cls.org1,
            nome="Alpha",
            cnpj=CNPJ().generate(),
            tipo="mei",
            municipio="X",
            estado="SC",
        )

    def test_favoritar_e_listar(self):
        self.client.force_authenticate(self.user1)
        url = reverse("empresas_api:empresa-favoritar", args=[self.empresa.id])
        resp = self.client.post(url)
        self.assertEqual(resp.status_code, 201)
        self.assertTrue(
            FavoritoEmpresa.objects.filter(usuario=self.user1, empresa=self.empresa, deleted=False).exists()
        )
        list_url = reverse("empresas_api:empresa-favoritos")
        resp = self.client.get(list_url)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.data), 1)
        detail_url = reverse("empresas_api:empresa-detail", args=[self.empresa.id])
        resp = self.client.get(detail_url)
        self.assertTrue(resp.data["favoritado"])

    def test_favoritar_outra_organizacao(self):
        self.client.force_authenticate(self.user2)
        url = reverse("empresas_api:empresa-favoritar", args=[self.empresa.id])
        resp = self.client.post(url)
        self.assertEqual(resp.status_code, 403)
        self.assertFalse(
            FavoritoEmpresa.objects.filter(usuario=self.user2, empresa=self.empresa, deleted=False).exists()
        )
