import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError

from feed.models import Comment, Post, Reacao


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
    Reacao.objects.create(post=post, user=admin_user, vote="like")

    assert post.comments.count() == 2
    assert post.reacoes.filter(vote="like", deleted=False).count() == 1


@pytest.mark.django_db
def test_reaction_uniqueness(admin_user, organizacao):
    post = Post.objects.create(autor=admin_user, organizacao=organizacao)
    Reacao.objects.create(post=post, user=admin_user, vote="like")
    with pytest.raises(IntegrityError):
        Reacao.objects.create(post=post, user=admin_user, vote="like")


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


@pytest.mark.django_db
def test_requires_nucleo(admin_user, organizacao):
    post = Post(
        autor=admin_user,
        organizacao=organizacao,
        tipo_feed="nucleo",
        conteudo="x",
    )
    with pytest.raises(ValidationError):
        post.full_clean()


@pytest.mark.django_db
def test_requires_evento(admin_user, organizacao):
    post = Post(
        autor=admin_user,
        organizacao=organizacao,
        tipo_feed="evento",
        conteudo="y",
    )
    with pytest.raises(ValidationError):
        post.full_clean()
