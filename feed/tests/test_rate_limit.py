from django.test import TestCase, override_settings
from django_ratelimit.core import is_ratelimited
from rest_framework.test import APIClient, APIRequestFactory

from accounts.factories import UserFactory
from organizacoes.factories import OrganizacaoFactory


class RateLimitTest(TestCase):
    def setUp(self):
        self.org = OrganizacaoFactory(rate_limit_multiplier=1)
        self.user = UserFactory(organizacao=self.org)
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    @override_settings(FEED_RATE_LIMIT_POST="2/m", FEED_RATE_LIMIT_READ="2/m")
    def test_post_rate_limit(self):
        for i in range(2):
            self.client.post(
                "/api/feed/posts/", {"conteudo": f"t{i}", "tipo_feed": "global"}
            )
        req = APIRequestFactory().post("/api/feed/posts/")
        req.user = self.user
        limited = is_ratelimited(
            req,
            group="feed_posts_create",
            key="user",
            rate="2/m",
            method="POST",
            increment=False,
        )
        self.assertTrue(limited)

    @override_settings(FEED_RATE_LIMIT_POST="1/m", FEED_RATE_LIMIT_READ="1/m")
    def test_multiplier(self):
        org2 = OrganizacaoFactory(rate_limit_multiplier=2)
        user2 = UserFactory(organizacao=org2)
        client2 = APIClient()
        client2.force_authenticate(user2)
        client2.post(
            "/api/feed/posts/", {"conteudo": "a", "tipo_feed": "global"}
        )
        client2.post(
            "/api/feed/posts/", {"conteudo": "b", "tipo_feed": "global"}
        )
        req = APIRequestFactory().post("/api/feed/posts/")
        req.user = user2
        limited = is_ratelimited(
            req,
            group="feed_posts_create",
            key="user",
            rate="1/m",
            method="POST",
            increment=False,
        )
        self.assertTrue(limited)
