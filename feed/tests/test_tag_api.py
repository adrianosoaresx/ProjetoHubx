from django.test import TestCase
from rest_framework.test import APIClient

from accounts.factories import UserFactory
from organizacoes.factories import OrganizacaoFactory
from feed.models import Tag


class TagAPITest(TestCase):
    def setUp(self) -> None:
        org = OrganizacaoFactory()
        self.user = UserFactory(organizacao=org)
        self.user.set_password("pass123")
        self.user.save()
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def test_create_tag(self):
        res = self.client.post("/api/feed/tags/", {"nome": "nova"})
        self.assertEqual(res.status_code, 201)
        self.assertEqual(res.data["nome"], "nova")

    def test_list_tags(self):
        Tag.objects.create(nome="tag1")
        res = self.client.get("/api/feed/tags/")
        self.assertEqual(res.status_code, 200)
        nomes = [item["nome"] for item in res.data]
        self.assertIn("tag1", nomes)

    def test_update_tag(self):
        tag = Tag.objects.create(nome="old")
        res = self.client.patch(f"/api/feed/tags/{tag.id}/", {"nome": "new"})
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data["nome"], "new")

    def test_delete_tag(self):
        tag = Tag.objects.create(nome="temp")
        res = self.client.delete(f"/api/feed/tags/{tag.id}/")
        self.assertEqual(res.status_code, 204)
        res = self.client.get("/api/feed/tags/")
        nomes = [item["nome"] for item in res.data]
        self.assertNotIn("temp", nomes)
