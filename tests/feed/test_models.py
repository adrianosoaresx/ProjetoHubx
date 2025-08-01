import pytest
from django.db import IntegrityError

from feed.models import Comment, Like, Post


@pytest.mark.django_db
def test_post_creation(admin_user, organizacao):
    post = Post.objects.create(
        autor=admin_user,
        organizacao=organizacao,
        tipo_feed="global",
        conteudo="Hello",
    )
    assert post.pk is not None
    assert Post._meta.ordering == ["-created_at"]


@pytest.mark.django_db
def test_post_relationships(admin_user, organizacao):
    post = Post.objects.create(
        autor=admin_user,
        organizacao=organizacao,
        tipo_feed="global",
    )
    Comment.objects.create(post=post, user=admin_user, texto="c1")
    Comment.objects.create(post=post, user=admin_user, texto="c2")
    Like.objects.create(post=post, user=admin_user)

    assert post.comments.count() == 2
    assert post.likes.count() == 1


@pytest.mark.django_db
def test_like_uniqueness(admin_user, organizacao):
    post = Post.objects.create(autor=admin_user, organizacao=organizacao)
    Like.objects.create(post=post, user=admin_user)
    with pytest.raises(IntegrityError):
        Like.objects.create(post=post, user=admin_user)


@pytest.mark.django_db
def test_nested_comments(admin_user, organizacao):
    post = Post.objects.create(autor=admin_user, organizacao=organizacao)
    parent = Comment.objects.create(post=post, user=admin_user, texto="c1")
    Comment.objects.create(post=post, user=admin_user, texto="c2", reply_to=parent)

    assert parent.replies.count() == 1


@pytest.mark.django_db
def test_soft_delete(admin_user, organizacao):
    post = Post.objects.create(autor=admin_user, organizacao=organizacao)
    post.soft_delete()
    post.refresh_from_db()
    assert post.deleted is True
