from unittest.mock import patch

import pytest

from feed.models import Comment, Like, Post


@patch("feed.signals.enviar_para_usuario")
@pytest.mark.django_db
def test_like_triggers_notification(mock_send, admin_user, organizacao):
    post = Post.objects.create(autor=admin_user, organizacao=organizacao)
    Like.objects.create(post=post, user=admin_user)
    assert mock_send.called


@patch("feed.signals.enviar_para_usuario")
@pytest.mark.django_db
def test_comment_triggers_notification(mock_send, admin_user, organizacao):
    post = Post.objects.create(autor=admin_user, organizacao=organizacao)
    Comment.objects.create(post=post, user=admin_user, texto="x")
    assert mock_send.called
