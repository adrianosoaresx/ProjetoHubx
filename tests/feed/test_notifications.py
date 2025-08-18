from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase

from feed.models import Comment, Like, Post
from feed.tasks import (
    NOTIFICATIONS_SENT,
    notificar_autor_sobre_interacao,
    notify_post_moderated,
)
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
        Like.objects.create(post=post, user=self.other)
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
        notificar_autor_sobre_interacao(str(self.post.id), "like")
        self.assertEqual(NOTIFICATIONS_SENT._value.get(), 1.0)

    @patch("feed.tasks.enviar_para_usuario")
    def test_moderation_increments_metric(self, mock_enviar):
        NOTIFICATIONS_SENT._value.set(0)
        notify_post_moderated(str(self.post.id), "aprovado")
        self.assertEqual(NOTIFICATIONS_SENT._value.get(), 1.0)
