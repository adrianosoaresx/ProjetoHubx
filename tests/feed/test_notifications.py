from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase

from feed.models import Comment, Like, Post
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
