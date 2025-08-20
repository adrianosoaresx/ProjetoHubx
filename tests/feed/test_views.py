import pytest
from django.contrib.messages import get_messages
from django.core.files.uploadedfile import SimpleUploadedFile
from django.http import HttpResponseForbidden
from django.urls import reverse

from feed.models import Comment, Post, Reacao, Tag

pytestmark = pytest.mark.django_db


def test_feedlist_global(client, admin_user, nucleado_user, posts):
    client.force_login(admin_user)
    url = reverse("feed:listar")
    resp = client.get(url)
    assert resp.status_code == 200
    assert all(p.tipo_feed == "global" for p in resp.context["posts"])

    client.force_login(nucleado_user)
    resp2 = client.get(url)
    assert all(p.organizacao == nucleado_user.organizacao for p in resp2.context["posts"])


def test_feedlist_usuario(client, nucleado_user, admin_user, posts):
    client.force_login(nucleado_user)
    url = reverse("feed:listar") + "?tipo_feed=usuario"
    resp = client.get(url)
    ids = {p.id for p in resp.context["posts"]}
    assert posts[1].id in ids
    assert posts[0].id in ids


def test_feedlist_nucleo(client, nucleado_user, posts, nucleo):
    client.force_login(nucleado_user)
    url = reverse("feed:listar") + f"?tipo_feed=nucleo&nucleo={nucleo.id}"
    resp = client.get(url)
    assert list(resp.context["posts"]) == [posts[2]]

    url = reverse("feed:listar") + "?tipo_feed=nucleo&nucleo=9999"
    resp2 = client.get(url)
    assert list(resp2.context["posts"]) == []


def test_feedlist_evento(client, nucleado_user, posts, evento):
    client.force_login(nucleado_user)
    url = reverse("feed:listar") + f"?tipo_feed=evento&evento={evento.id}"
    resp = client.get(url)
    assert list(resp.context["posts"]) == [posts[3]]


def test_feedlist_search(client, nucleado_user, posts):
    client.force_login(nucleado_user)
    Post.objects.create(
        autor=nucleado_user, organizacao=nucleado_user.organizacao, conteudo="busca", tipo_feed="global"
    )
    url = reverse("feed:listar") + "?q=busca"
    resp = client.get(url)
    assert all("busca" in p.conteudo for p in resp.context["posts"])


def test_novapostagem_root_forbidden(client, root_user):
    client.force_login(root_user)
    resp = client.get(reverse("feed:nova_postagem"))
    assert resp.status_code == 403 or isinstance(resp, HttpResponseForbidden)


def test_novapostagem_create(client, associado_user):
    client.force_login(associado_user)
    data = {"tipo_feed": "global", "conteudo": "ola"}
    resp = client.post(reverse("feed:nova_postagem"), data)
    assert resp.status_code == 302
    post = Post.objects.order_by("-created_at").first()
    assert post.autor == associado_user
    assert post.organizacao == associado_user.organizacao


def test_novapostagem_file_upload(client, associado_user):
    client.force_login(associado_user)
    pdf = SimpleUploadedFile("file.pdf", b"data", content_type="application/pdf")
    resp = client.post(reverse("feed:nova_postagem"), {"tipo_feed": "global", "arquivo": pdf})
    assert resp.status_code in {302, 204}
    post = Post.objects.order_by("-created_at").first()
    assert post.pdf


def test_create_comment(client, nucleado_user, posts):
    client.force_login(nucleado_user)
    post = posts[0]
    url = reverse("feed:create_comment", args=[post.id])
    resp = client.post(url, {"texto": "Oi"})
    assert resp.status_code == 302
    comment = Comment.objects.get(post=post, user=nucleado_user)
    assert comment.texto == "Oi"


def test_toggle_like(client, nucleado_user, posts):
    client.force_login(nucleado_user)
    post = posts[0]
    url = reverse("feed:toggle_like", args=[post.id])
    client.post(url)
    assert Reacao.objects.filter(post=post, user=nucleado_user, vote="like", deleted=False).exists()
    client.post(url)
    assert Reacao.all_objects.filter(post=post, user=nucleado_user, vote="like", deleted=True).exists()


def test_post_update_permissions(client, nucleado_user, admin_user, posts):
    post = posts[0]
    client.force_login(nucleado_user)
    url = reverse("feed:post_update", args=[post.id])
    resp = client.post(url, {"tipo_feed": "global", "conteudo": "x"})
    assert resp.status_code == 302
    msg = list(get_messages(resp.wsgi_request))[0].message.lower()
    assert "permissão" in msg

    client.force_login(admin_user)
    img = SimpleUploadedFile("pic.png", b"data", content_type="image/png")
    resp2 = client.post(url, {"tipo_feed": "global", "conteudo": "y", "arquivo": img})
    assert resp2.status_code == 200
    post.refresh_from_db()
    assert post.image.name == ""


def test_post_delete(client, admin_user, posts):
    post = posts[0]
    url = reverse("feed:post_delete", args=[post.id])
    client.force_login(admin_user)
    resp = client.post(url)
    assert resp.status_code == 302
    post.refresh_from_db()
    assert post.deleted is True


def test_video_upload(client, associado_user):
    client.force_login(associado_user)
    video = SimpleUploadedFile("vid.mp4", b"d", content_type="video/mp4")
    resp = client.post(reverse("feed:nova_postagem"), {"tipo_feed": "global", "arquivo": video})
    assert resp.status_code == 302
    post = Post.objects.order_by("-created_at").first()
    assert post.video


def test_filter_by_tags(client, nucleado_user):
    client.force_login(nucleado_user)
    tag = Tag.objects.create(nome="python")
    post = Post.objects.create(
        autor=nucleado_user,
        organizacao=nucleado_user.organizacao,
        tipo_feed="global",
        conteudo="tagged",
    )
    post.tags.add(tag)
    url = reverse("feed:listar") + "?tags=python"
    resp = client.get(url)
    assert list(resp.context["posts"]) == [post]


def test_meu_mural(client, nucleado_user, posts):
    client.force_login(nucleado_user)
    url = reverse("feed:meu_mural")
    resp = client.get(url)
    contents = [p.conteudo for p in resp.context.get("posts", [])]
    assert posts[1].conteudo in contents
    assert posts[0].conteudo in contents
    assert posts[2].conteudo in contents
    assert posts[3].conteudo in contents
