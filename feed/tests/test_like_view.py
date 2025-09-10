from django.test import TestCase, override_settings
from django.urls import reverse
from unittest.mock import patch

from accounts.factories import UserFactory
from feed.factories import PostFactory
from feed.models import Reacao
from organizacoes.factories import OrganizacaoFactory


@override_settings(ROOT_URLCONF="Hubx.urls", FEED_RATE_LIMIT_READ="1/m")
class ToggleLikeRateLimitTest(TestCase):
    def setUp(self) -> None:
        org = OrganizacaoFactory()
        self.user = UserFactory(organizacao=org)
        self.post = PostFactory(autor=self.user, organizacao=org)
        self.client.force_login(self.user)

    @patch("feed.tasks.enviar_para_usuario")
    def test_toggle_like_rate_limited(self, enviar) -> None:
        url = reverse("feed:toggle_like", args=[self.post.id])
        first = self.client.post(url)
        self.assertEqual(first.status_code, 302)
        self.assertTrue(Reacao.objects.filter(post=self.post, user=self.user, vote="like", deleted=False).exists())
        second = self.client.post(url)
        self.assertEqual(second.status_code, 429)
        self.assertTrue(Reacao.objects.filter(post=self.post, user=self.user, vote="like", deleted=False).exists())
