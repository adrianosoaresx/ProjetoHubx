from django.test import TestCase, override_settings
from rest_framework.test import APIClient
from unittest.mock import patch

from accounts.factories import UserFactory
from feed.factories import PostFactory
from feed.api import REACTIONS_TOTAL
from feed.models import Reacao
from organizacoes.factories import OrganizacaoFactory

@override_settings(ROOT_URLCONF="Hubx.urls")
class ReactionToggleAPITest(TestCase):
    def setUp(self) -> None:
        org = OrganizacaoFactory()
        self.user = UserFactory(organizacao=org)
        self.client = APIClient()
        self.client.force_authenticate(self.user)
        self.post = PostFactory(autor=self.user, organizacao=org)

    @patch("feed.tasks.enviar_para_usuario")
    def test_toggle_reaction(self, enviar):
        base_count = REACTIONS_TOTAL.labels(vote="like")._value.get()
        url = f"/api/feed/posts/{self.post.id}/reacoes/"

        res = self.client.post(url, {"vote": "like"})
        self.assertEqual(res.status_code, 201)
        self.assertTrue(
            Reacao.objects.filter(
                post=self.post, user=self.user, vote="like", deleted=False
            ).exists()
        )
        self.assertEqual(
            REACTIONS_TOTAL.labels(vote="like")._value.get(), base_count + 1
        )
        res_get = self.client.get(url)
        self.assertEqual(res_get.data["like"], 1)
        self.assertEqual(res_get.data["user_reaction"], "like")

        res = self.client.post(url, {"vote": "like"})
        self.assertEqual(res.status_code, 204)
        self.assertTrue(
            Reacao.all_objects.filter(
                post=self.post, user=self.user, vote="like", deleted=True
            ).exists()
        )
        self.assertEqual(
            REACTIONS_TOTAL.labels(vote="like")._value.get(), base_count
        )
        res_get = self.client.get(url)
        self.assertEqual(res_get.data["like"], 0)
        self.assertIsNone(res_get.data["user_reaction"])

    @patch("feed.tasks.enviar_para_usuario")
    def test_share_reaction(self, enviar):
        base_count = REACTIONS_TOTAL.labels(vote="share")._value.get()
        url = f"/api/feed/posts/{self.post.id}/reacoes/"
        res = self.client.post(url, {"vote": "share"})
        self.assertEqual(res.status_code, 201)
        self.assertTrue(
            Reacao.objects.filter(
                post=self.post, user=self.user, vote="share", deleted=False
            ).exists()
        )
        self.assertEqual(
            REACTIONS_TOTAL.labels(vote="share")._value.get(), base_count + 1
        )
        res = self.client.post(url, {"vote": "share"})
        self.assertEqual(res.status_code, 204)
        self.assertTrue(
            Reacao.all_objects.filter(
                post=self.post, user=self.user, vote="share", deleted=True
            ).exists()
        )
        self.assertEqual(
            REACTIONS_TOTAL.labels(vote="share")._value.get(), base_count
        )
