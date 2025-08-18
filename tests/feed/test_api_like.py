import pytest
from feed.models import Post, Like

pytestmark = pytest.mark.django_db


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
    resp = client.post(url)
    assert resp.status_code == 201
    assert Like.objects.filter(post=post, user=nucleado_user).exists()
    resp = client.post(url)
    assert resp.status_code == 200
    assert not Like.objects.filter(post=post, user=nucleado_user).exists()


def test_likeviewset_prevents_manipulating_others(client, nucleado_user, admin_user, organizacao):
    post = Post.objects.create(
        autor=admin_user,
        organizacao=organizacao,
        tipo_feed="global",
        conteudo="x",
    )
    post.moderacao.status = "aprovado"
    post.moderacao.save()
    like = Like.objects.create(post=post, user=admin_user)
    client.force_login(nucleado_user)
    resp = client.delete(f"/api/feed/likes/{like.id}/")
    assert resp.status_code == 404
