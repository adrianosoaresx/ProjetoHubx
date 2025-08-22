from django.test import TestCase, override_settings
from rest_framework.test import APIClient
from unittest.mock import patch

from accounts.factories import UserFactory
from feed.factories import PostFactory
from feed.api import REACTIONS_TOTAL
from feed.models import Reacao
from organizacoes.factories import OrganizacaoFactory

@override_settings(ROOT_URLCONF="Hubx.urls")
class LikeAPITest(TestCase):
    def setUp(self) -> None:
        org = OrganizacaoFactory()
        self.user = UserFactory(organizacao=org)
        self.client = APIClient()
        self.client.force_authenticate(self.user)
        self.post = PostFactory(autor=self.user, organizacao=org)

    @patch("feed.tasks.enviar_para_usuario")
    def test_toggle_like(self, enviar):
        base_count = REACTIONS_TOTAL.labels(vote="like")._value.get()
        res = self.client.post("/api/feed/likes/", {"post": self.post.id})
        self.assertEqual(res.status_code, 201)
        self.assertTrue(
            Reacao.objects.filter(
                post=self.post, user=self.user, vote="like", deleted=False
            ).exists()
        )
        self.assertEqual(
            REACTIONS_TOTAL.labels(vote="like")._value.get(), base_count + 1
        )
        res = self.client.post("/api/feed/likes/", {"post": self.post.id})
        self.assertEqual(res.status_code, 200)
        self.assertTrue(
            Reacao.all_objects.filter(
                post=self.post, user=self.user, vote="like", deleted=True
            ).exists()
        )
        self.assertEqual(
            REACTIONS_TOTAL.labels(vote="like")._value.get(), base_count
        )
