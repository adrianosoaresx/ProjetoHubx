from __future__ import annotations

from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from accounts.factories import UserFactory
from feed.factories import PostFactory
from feed.models import Tag
from organizacoes.factories import OrganizacaoFactory


@override_settings(ROOT_URLCONF="Hubx.urls")
class FeedSearchTest(TestCase):
    def setUp(self) -> None:
        org = OrganizacaoFactory()
        self.user = UserFactory(organizacao=org)
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def _ids(self, data) -> list[str]:
        results = data["results"] if isinstance(data, dict) else data
        return [item["id"] for item in results]

    def test_simple_search(self) -> None:
        p1 = PostFactory(autor=self.user, conteudo="abacate verde")
        p2 = PostFactory(autor=self.user, conteudo="laranja doce")
        res = self.client.get("/api/feed/posts/", {"q": "abacate"})
        ids = self._ids(res.data)
        self.assertIn(str(p1.id), ids)
        self.assertNotIn(str(p2.id), ids)

    def test_or_operator(self) -> None:
        p1 = PostFactory(autor=self.user, conteudo="abacate verde")
        p2 = PostFactory(autor=self.user, conteudo="laranja doce")
        res = self.client.get("/api/feed/posts/", {"q": "abacate|laranja"})
        ids = self._ids(res.data)
        self.assertIn(str(p1.id), ids)
        self.assertIn(str(p2.id), ids)

    def test_post_with_multiple_tags_returns_once(self) -> None:
        post = PostFactory(autor=self.user)
        tag1 = Tag.objects.create(nome="abacate")
        tag2 = Tag.objects.create(nome="laranja")
        post.tags.add(tag1, tag2)
        res = self.client.get("/api/feed/posts/", {"q": "abacate|laranja"})
        ids = self._ids(res.data)
        self.assertEqual(ids.count(str(post.id)), 1)
