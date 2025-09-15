from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase

from feed.models import Comment, Post, Reacao
from feed.tasks import (
    NOTIFICATIONS_SENT,
    notificar_autor_sobre_interacao,
    notify_post_moderated,
)
from notificacoes.models import NotificationTemplate
from organizacoes.models import Organizacao


class NotificationTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.org = Organizacao.objects.create(nome="Org", cnpj="00.000.000/0001-00")
        self.author = User.objects.create_user(
            email="author@example.com", username="author", password="pass", organizacao=self.org
        )
        self.other = User.objects.create_user(
            email="other@example.com", username="other", password="pass", organizacao=self.org
        )

    @patch("feed.signals.notificar_autor_sobre_interacao")
    def test_like_triggers_task(self, mock_task):
        post = Post.objects.create(autor=self.author, organizacao=self.org, conteudo="hi")
        Reacao.objects.create(post=post, user=self.other, vote="like")
        mock_task.assert_called_once_with(post.id, "like")

    @patch("feed.signals.notificar_autor_sobre_interacao")
    def test_comment_triggers_task(self, mock_task):
        post = Post.objects.create(autor=self.author, organizacao=self.org, conteudo="hi")
        Comment.objects.create(post=post, user=self.other, texto="oi")
        mock_task.assert_called_once_with(post.id, "comment")


class NotificationMetricsTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.org = Organizacao.objects.create(nome="Org", cnpj="00.000.000/0001-00")
        self.author = User.objects.create_user(
            email="author@example.com", username="author", password="pass", organizacao=self.org
        )
        self.post = Post.objects.create(autor=self.author, organizacao=self.org, conteudo="hi")

    @patch("feed.tasks.enviar_para_usuario")
    def test_like_increments_metric(self, mock_enviar):
        NOTIFICATIONS_SENT._value.set(0)
        self.assertTrue(NotificationTemplate.objects.filter(codigo="feed_like").exists())
        notificar_autor_sobre_interacao(str(self.post.id), "like")
        mock_enviar.assert_called_once_with(self.author, "feed_like", {"post_id": str(self.post.id)})
        self.assertEqual(NOTIFICATIONS_SENT._value.get(), 1.0)

    @patch("feed.tasks.enviar_para_usuario")
    def test_moderation_increments_metric(self, mock_enviar):
        NOTIFICATIONS_SENT._value.set(0)
        notify_post_moderated(str(self.post.id), "aprovado")
        self.assertEqual(NOTIFICATIONS_SENT._value.get(), 1.0)

    @patch("feed.tasks.enviar_para_usuario")
    def test_comment_uses_comment_template(self, mock_enviar):
        NOTIFICATIONS_SENT._value.set(0)
        self.assertTrue(NotificationTemplate.objects.filter(codigo="feed_comment").exists())
        notificar_autor_sobre_interacao(str(self.post.id), "comment")
        mock_enviar.assert_called_once_with(self.author, "feed_comment", {"post_id": str(self.post.id)})
        self.assertEqual(NOTIFICATIONS_SENT._value.get(), 1.0)
