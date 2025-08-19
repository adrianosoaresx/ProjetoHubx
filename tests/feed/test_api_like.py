import pytest
from unittest.mock import patch
from django.test import override_settings

from feed.api import LIKES_TOTAL
from feed.models import Like, Post

pytestmark = pytest.mark.django_db


@override_settings(ROOT_URLCONF="Hubx.urls")
def test_toggle_like(client, nucleado_user, organizacao):
    post = Post.objects.create(
        autor=nucleado_user,
        organizacao=organizacao,
        tipo_feed="global",
        conteudo="x",
    )
    post.moderacao.status = "aprovado"
    post.moderacao.save()
    client.force_login(nucleado_user)
    url = f"/api/feed/posts/{post.id}/toggle_like/"
    LIKES_TOTAL._value.set(0)
    with patch("feed.signals.notificar_autor_sobre_interacao"):
        resp = client.post(url)
        assert resp.status_code == 201
        assert Like.objects.filter(post=post, user=nucleado_user).exists()
        assert LIKES_TOTAL._value.get() == 1
        resp = client.post(url)
        assert resp.status_code == 200
        assert not Like.objects.filter(post=post, user=nucleado_user).exists()
        assert LIKES_TOTAL._value.get() == 0


@override_settings(ROOT_URLCONF="Hubx.urls")
def test_likeviewset_prevents_manipulating_others(client, nucleado_user, admin_user, organizacao):
    post = Post.objects.create(
        autor=admin_user,
        organizacao=organizacao,
        tipo_feed="global",
        conteudo="x",
    )
    post.moderacao.status = "aprovado"
    post.moderacao.save()
    with patch("feed.signals.notificar_autor_sobre_interacao"):
        like = Like.objects.create(post=post, user=admin_user)
    client.force_login(nucleado_user)
    resp = client.delete(f"/api/feed/likes/{like.id}/")
    assert resp.status_code == 404


@override_settings(ROOT_URLCONF="Hubx.urls")
def test_likeviewset_toggle(client, nucleado_user, organizacao):
    post = Post.objects.create(
        autor=nucleado_user,
        organizacao=organizacao,
        tipo_feed="global",
        conteudo="x",
    )
    post.moderacao.status = "aprovado"
    post.moderacao.save()
    client.force_login(nucleado_user)
    url = "/api/feed/likes/"
    data = {"post": str(post.id)}
    LIKES_TOTAL._value.set(0)
    with patch("feed.signals.notificar_autor_sobre_interacao"):
        resp = client.post(url, data)
        assert resp.status_code == 201
        assert Like.objects.filter(post=post, user=nucleado_user).exists()
        assert LIKES_TOTAL._value.get() == 1
        resp = client.post(url, data)
        assert resp.status_code == 200
        assert not Like.objects.filter(post=post, user=nucleado_user).exists()
        assert LIKES_TOTAL._value.get() == 0
        resp = client.post(url, data)
        assert resp.status_code == 201
        assert Like.objects.filter(post=post, user=nucleado_user).exists()
        assert LIKES_TOTAL._value.get() == 1
