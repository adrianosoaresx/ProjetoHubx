from __future__ import annotations

from django.test import TestCase
from rest_framework.test import APIClient

from accounts.factories import UserFactory
from feed.factories import PostFactory
from organizacoes.factories import OrganizacaoFactory


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

