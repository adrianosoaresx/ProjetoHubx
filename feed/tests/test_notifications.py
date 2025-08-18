from __future__ import annotations

from unittest.mock import patch

from django.test import TestCase, override_settings

from accounts.factories import UserFactory
from organizacoes.factories import OrganizacaoFactory


@override_settings(CELERY_TASK_ALWAYS_EAGER=True)
class FeedNotificationTest(TestCase):
    def setUp(self) -> None:
        org = OrganizacaoFactory()
        self.user = UserFactory(organizacao=org)
        self.other = UserFactory(organizacao=org)

    @patch("feed.tasks.enviar_para_usuario")
    def test_notify_new_post_once(self, enviar) -> None:
        from feed.models import Post
        from feed.tasks import notify_new_post

        post = Post.objects.create(
            autor=self.user, organizacao=self.user.organizacao, conteudo="ola"
        )
        notify_new_post(str(post.id))
        self.assertEqual(enviar.call_count, 1)
        notify_new_post(str(post.id))
        self.assertEqual(enviar.call_count, 1)  # idempotente

    @patch("feed.tasks.enviar_para_usuario")
    def test_notify_like_once(self, enviar) -> None:
        from feed.models import Like, Post

        post = Post.objects.create(
            autor=self.other, organizacao=self.other.organizacao, conteudo="ola"
        )
        Like.objects.create(post=post, user=self.user)
        self.assertEqual(enviar.call_count, 1)

    @patch("feed.tasks.enviar_para_usuario")
    def test_notify_comment_once(self, enviar) -> None:
        from feed.models import Comment, Post

        post = Post.objects.create(
            autor=self.other, organizacao=self.other.organizacao, conteudo="ola"
        )
        Comment.objects.create(post=post, user=self.user, texto="oi")
        self.assertEqual(enviar.call_count, 1)

