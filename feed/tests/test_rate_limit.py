from django.conf import settings
from django.test import TestCase, override_settings
from rest_framework.test import APIClient, APIRequestFactory

from accounts.factories import UserFactory
from organizacoes.factories import OrganizacaoFactory

from feed import api as feed_api


@override_settings(ROOT_URLCONF="Hubx.urls")
class RateLimitTest(TestCase):
    def setUp(self):
        self.org = OrganizacaoFactory(rate_limit_multiplier=1)
        self.user = UserFactory(organizacao=self.org)
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    @override_settings(FEED_RATE_LIMIT_POST="2/m", FEED_RATE_LIMIT_READ="2/m")
    def test_post_rate_limit(self):
        for i in range(2):
            res = self.client.post("/api/feed/posts/", {"conteudo": f"t{i}", "tipo_feed": "global"})
            self.assertEqual(res.status_code, 201)

        req = APIRequestFactory().post("/api/feed/posts/")
        req.user = self.user
        self.assertEqual(feed_api._post_rate(None, req), "2/m")

    @override_settings(FEED_RATE_LIMIT_POST="1/m", FEED_RATE_LIMIT_READ="1/m")
    def test_multiplier(self):
        org2 = OrganizacaoFactory(rate_limit_multiplier=2)
        user2 = UserFactory(organizacao=org2)
        client2 = APIClient()
        client2.force_authenticate(user2)
        res1 = client2.post("/api/feed/posts/", {"conteudo": "a", "tipo_feed": "global"})
        self.assertEqual(res1.status_code, 201)
        res2 = client2.post("/api/feed/posts/", {"conteudo": "b", "tipo_feed": "global"})
        self.assertEqual(res2.status_code, 201)
        req = APIRequestFactory().post("/api/feed/posts/")
        req.user = user2
        self.assertEqual(feed_api._post_rate(None, req), "2/m")

    @override_settings()
    def test_post_rate_limit_default_when_setting_missing(self):
        if hasattr(settings, "FEED_RATE_LIMIT_POST"):
            delattr(settings, "FEED_RATE_LIMIT_POST")

        response = self.client.post("/api/feed/posts/", {"conteudo": "fallback", "tipo_feed": "global"})
        self.assertEqual(response.status_code, 201)

        req = APIRequestFactory().post("/api/feed/posts/")
        req.user = self.user
        self.assertEqual(feed_api._post_rate(None, req), "20/m")

    @override_settings()
    def test_read_rate_limit_default_when_setting_missing(self):
        if hasattr(settings, "FEED_RATE_LIMIT_READ"):
            delattr(settings, "FEED_RATE_LIMIT_READ")

        response = self.client.get("/api/feed/posts/")
        self.assertEqual(response.status_code, 200)

        req = APIRequestFactory().get("/api/feed/posts/")
        req.user = self.user
        self.assertEqual(feed_api._read_rate(None, req), "100/m")
