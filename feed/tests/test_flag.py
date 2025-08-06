from __future__ import annotations

from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from accounts.factories import UserFactory
from organizacoes.factories import OrganizacaoFactory
from feed.models import Post


class FlagAPITest(TestCase):
    def setUp(self) -> None:
        org = OrganizacaoFactory()
        self.user = UserFactory(organizacao=org)
        self.user.set_password("pass123")
        self.user.save()
        self.client = APIClient()
        self.client.force_authenticate(self.user)
        self.post = Post.objects.create(autor=self.user, organizacao=org, tipo_feed="global")

    @override_settings(FEED_FLAGS_LIMIT=1)
    def test_flag_post(self):
        res1 = self.client.post(f"/api/feed/posts/{self.post.id}/flag/")
        self.assertEqual(res1.status_code, 204)
        self.post.refresh_from_db()
        self.assertEqual(self.post.moderacao.status, "pendente")
        res2 = self.client.post(f"/api/feed/posts/{self.post.id}/flag/")
        self.assertEqual(res2.status_code, 400)
