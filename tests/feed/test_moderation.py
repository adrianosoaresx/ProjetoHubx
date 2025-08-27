from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from feed.models import ModeracaoPost, Post
from organizacoes.models import Organizacao


class ModerationTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.org = Organizacao.objects.create(nome="Org", cnpj="00.000.000/0001-00")
        self.admin = User.objects.create_superuser(
            email="admin@example.com", username="admin", password="pass", organizacao=self.org
        )
        self.author = User.objects.create_user(
            email="author@example.com", username="author", password="pass", organizacao=self.org
        )
        self.other = User.objects.create_user(
            email="other@example.com", username="other", password="pass", organizacao=self.org
        )
        self.client = APIClient()

    def _list(self, user):
        self.client.force_authenticate(user=user)
        resp = self.client.get("/api/feed/posts/")
        self.client.force_authenticate(user=None)
        return resp

    def test_pending_visibility_and_approval(self):
        post = Post.objects.create(autor=self.author, organizacao=self.org, conteudo="hi")
        self.assertIsNone(post.moderacao)

        resp = self._list(self.other)
        data = resp.data if isinstance(resp.data, dict) else {"results": resp.data}
        self.assertEqual(len(data["results"]), 0)

        resp = self._list(self.author)
        data = resp.data if isinstance(resp.data, dict) else {"results": resp.data}
        self.assertEqual(len(data["results"]), 1)

        resp = self._list(self.admin)
        data = resp.data if isinstance(resp.data, dict) else {"results": resp.data}
        self.assertEqual(len(data["results"]), 1)

        self.client.force_authenticate(user=self.admin)
        resp = self.client.post(
            f"/api/feed/posts/{post.id}/avaliar/",
            {"status": "aprovado"},
            format="json",
        )
        self.assertEqual(resp.status_code, 200)
        post.refresh_from_db()
        self.assertEqual(post.moderacao.status, "aprovado")
        self.assertEqual(post.moderacao.avaliado_por, self.admin)
        self.client.force_authenticate(user=None)

        resp = self._list(self.other)
        data = resp.data if isinstance(resp.data, dict) else {"results": resp.data}
        self.assertEqual(len(data["results"]), 1)

    def test_rejected_hidden(self):
        post = Post.objects.create(autor=self.author, organizacao=self.org, conteudo="hi")
        ModeracaoPost.objects.create(post=post, status="rejeitado")

        resp = self._list(self.author)
        data = resp.data if isinstance(resp.data, dict) else {"results": resp.data}
        self.assertEqual(len(data["results"]), 0)

    def test_multiple_manual_decisions_create_history(self):
        post = Post.objects.create(autor=self.author, organizacao=self.org, conteudo="hi")
        self.client.force_authenticate(user=self.admin)
        self.client.post(
            f"/api/feed/posts/{post.id}/avaliar/",
            {"status": "aprovado"},
            format="json",
        )
        self.client.post(
            f"/api/feed/posts/{post.id}/avaliar/",
            {"status": "rejeitado"},
            format="json",
        )
        self.client.force_authenticate(user=None)
        self.assertEqual(ModeracaoPost.objects.filter(post=post).count(), 2)
        self.assertEqual(post.moderacao.status, "rejeitado")
