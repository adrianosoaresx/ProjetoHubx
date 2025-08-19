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


    @patch("feed.tasks.capture_exception")
    @patch("feed.tasks.enviar_para_usuario", side_effect=Exception("err"))
    def test_notificar_autor_capture_exception(self, enviar, capture) -> None:
        from django.conf import settings
        from feed.factories import PostFactory
        from feed.tasks import NOTIFICATIONS_SENT, notificar_autor_sobre_interacao

        settings.CELERY_TASK_EAGER_PROPAGATES = False
        post = PostFactory(autor=self.user, organizacao=self.user.organizacao)

        NOTIFICATIONS_SENT._value.set(0)
        result = notificar_autor_sobre_interacao.delay(str(post.id), "like")

        with self.assertRaises(Exception):
            result.get()

        self.assertEqual(NOTIFICATIONS_SENT._value.get(), 0)
        self.assertEqual(enviar.call_count, 4)
        self.assertEqual(capture.call_count, 4)

    @patch("feed.tasks.enviar_para_usuario")
    def test_notificar_autor_increments_metric(self, enviar) -> None:
        from feed.factories import PostFactory
        from feed.tasks import NOTIFICATIONS_SENT, notificar_autor_sobre_interacao

        NOTIFICATIONS_SENT._value.set(0)
        post = PostFactory(autor=self.user, organizacao=self.user.organizacao)

        notificar_autor_sobre_interacao(str(post.id), "like")

        self.assertEqual(NOTIFICATIONS_SENT._value.get(), 1.0)

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


