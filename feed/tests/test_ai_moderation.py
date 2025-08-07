from __future__ import annotations

from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from accounts.factories import UserFactory
from feed.forms import PostForm
from feed.models import ModeracaoPost
from organizacoes.factories import OrganizacaoFactory


@override_settings(FEED_BAD_WORDS=["ruim"], FEED_AI_THRESHOLDS={"suspeito": 0.1, "rejeitado": 0.2})
class AIModerationAPITest(TestCase):
    def setUp(self) -> None:
        org = OrganizacaoFactory()
        self.user = UserFactory(organizacao=org)
        self.user.set_password("pass123")
        self.user.save()
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def test_rejects_inappropriate_content(self):
        res = self.client.post(
            "/api/feed/posts/", {"conteudo": "ruim ruim", "tipo_feed": "global"}
        )
        self.assertEqual(res.status_code, 400)

    def test_flags_suspect_content(self):
        res = self.client.post(
            "/api/feed/posts/", {"conteudo": "ruim", "tipo_feed": "global"}
        )
        self.assertEqual(res.status_code, 201)
        post_id = res.data["id"]
        moderacao = ModeracaoPost.objects.get(post_id=post_id)
        self.assertEqual(moderacao.status, "pendente")


@override_settings(FEED_BAD_WORDS=["ruim"], FEED_AI_THRESHOLDS={"suspeito": 0.1, "rejeitado": 0.2})
class AIModerationFormTest(TestCase):
    def setUp(self) -> None:
        org = OrganizacaoFactory()
        self.user = UserFactory(organizacao=org)

    def test_form_rejects_content(self):
        form = PostForm(
            data={"tipo_feed": "global", "conteudo": "ruim ruim"}, user=self.user
        )
        self.assertFalse(form.is_valid())

    def test_form_flags_suspect(self):
        form = PostForm(
            data={"tipo_feed": "global", "conteudo": "ruim"}, user=self.user
        )
        self.assertTrue(form.is_valid())
        post = form.save()
        moderacao = post.moderacao
        self.assertEqual(moderacao.status, "pendente")
