from unittest.mock import patch

import pytest

from feed.models import Comment, Post, Reacao


@patch("feed.signals.notificar_autor_sobre_interacao")
@pytest.mark.django_db
def test_like_triggers_notification(mock_task, admin_user, organizacao):
    post = Post.objects.create(autor=admin_user, organizacao=organizacao)
    Reacao.objects.create(post=post, user=admin_user, vote="like")
    assert mock_task.called


@patch("feed.signals.notificar_autor_sobre_interacao")
@pytest.mark.django_db
def test_comment_triggers_notification(mock_task, admin_user, organizacao):
    post = Post.objects.create(autor=admin_user, organizacao=organizacao)
    Comment.objects.create(post=post, user=admin_user, texto="x")
    assert mock_task.called
