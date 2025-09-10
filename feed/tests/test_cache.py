from __future__ import annotations

from django.core.cache import cache

from feed.cache import invalidate_feed_cache
from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from rest_framework.test import APIClient

from accounts.factories import UserFactory
from feed.factories import PostFactory
from organizacoes.factories import OrganizacaoFactory


class FeedCacheTest(TestCase):
    def setUp(self) -> None:
        org = OrganizacaoFactory()
        self.user = UserFactory(organizacao=org)
        self.client = APIClient()
        self.client.force_authenticate(self.user)
        invalidate_feed_cache()

    def _get_ids(self, data) -> list[str]:
        results = data["results"] if isinstance(data, dict) else data
        return [item["id"] for item in results]

    def test_cache_miss_and_hit(self) -> None:
        PostFactory(autor=self.user, conteudo="primeiro")
        with CaptureQueriesContext(connection) as ctx1:
            res1 = self.client.get("/api/feed/posts/")
            self.assertEqual(res1.status_code, 200)
            self.assertGreater(len(ctx1), 0)
        with CaptureQueriesContext(connection) as ctx2:
            res2 = self.client.get("/api/feed/posts/")
            self.assertEqual(res2.status_code, 200)
            self.assertLess(len(ctx2), len(ctx1))
        self.assertEqual(self._get_ids(res1.data), self._get_ids(res2.data))

    def test_cache_invalidation(self) -> None:
        first = PostFactory(autor=self.user, conteudo="a")
        self.client.get("/api/feed/posts/")
        PostFactory(autor=self.user, conteudo="b")  # sinal limpa cache
        res = self.client.get("/api/feed/posts/")
        ids = self._get_ids(res.data)
        self.assertIn(str(first.id), ids)
        self.assertEqual(len(ids), 2)

    def test_invalidate_only_feed_keys(self) -> None:
        cache.set("other:key", "value", 60)
        PostFactory(autor=self.user, conteudo="a")
        self.client.get("/api/feed/posts/")
        PostFactory(autor=self.user, conteudo="b")
        self.assertEqual(cache.get("other:key"), "value")
