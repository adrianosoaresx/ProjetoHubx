from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from accounts.factories import UserFactory
from organizacoes.factories import OrganizacaoFactory
from feed.models import Tag


@override_settings(ROOT_URLCONF="Hubx.urls")
class TagAPITest(TestCase):
    def setUp(self) -> None:
        org = OrganizacaoFactory()
        self.admin = UserFactory(organizacao=org, is_staff=True)
        self.admin.set_password("pass123")
        self.admin.save()
        self.user = UserFactory(organizacao=org)
        self.user.set_password("pass123")
        self.user.save()
        self.client = APIClient()

    def test_list_tags_anonymous(self):
        Tag.objects.create(nome="tag1")
        res = APIClient().get("/api/feed/tags/")
        self.assertEqual(res.status_code, 200)
        self.assertIn("tag1", [item["nome"] for item in res.data])

    def test_admin_can_create_tag(self):
        self.client.force_authenticate(self.admin)
        res = self.client.post("/api/feed/tags/", {"nome": "nova"})
        self.assertEqual(res.status_code, 201)
        self.assertEqual(res.data["nome"], "nova")

    def test_admin_can_update_tag(self):
        tag = Tag.objects.create(nome="old")
        self.client.force_authenticate(self.admin)
        res = self.client.patch(f"/api/feed/tags/{tag.id}/", {"nome": "new"})
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data["nome"], "new")

    def test_admin_can_delete_tag(self):
        tag = Tag.objects.create(nome="temp")
        self.client.force_authenticate(self.admin)
        res = self.client.delete(f"/api/feed/tags/{tag.id}/")
        self.assertEqual(res.status_code, 204)

    def test_common_user_cannot_create_tag(self):
        self.client.force_authenticate(self.user)
        res = self.client.post("/api/feed/tags/", {"nome": "bloqueada"})
        self.assertEqual(res.status_code, 403)

    def test_common_user_cannot_update_tag(self):
        tag = Tag.objects.create(nome="old")
        self.client.force_authenticate(self.user)
        res = self.client.patch(f"/api/feed/tags/{tag.id}/", {"nome": "new"})
        self.assertEqual(res.status_code, 403)

    def test_common_user_cannot_delete_tag(self):
        tag = Tag.objects.create(nome="temp")
        self.client.force_authenticate(self.user)
        res = self.client.delete(f"/api/feed/tags/{tag.id}/")
        self.assertEqual(res.status_code, 403)
