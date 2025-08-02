import pytest
from django.contrib.contenttypes.models import ContentType
from django.urls import reverse

from discussao.forms import RespostaDiscussaoForm
from discussao.models import (
    CategoriaDiscussao,
    InteracaoDiscussao,
    RespostaDiscussao,
    TopicoDiscussao,
)
from nucleos.models import Nucleo

pytestmark = pytest.mark.django_db


@pytest.fixture
def categoria(organizacao):
    return CategoriaDiscussao.objects.create(nome="Cat", organizacao=organizacao)


@pytest.fixture
def categoria_outro(outra_organizacao):
    return CategoriaDiscussao.objects.create(nome="Outra", organizacao=outra_organizacao)


@pytest.fixture
def topico(categoria, admin_user):
    return TopicoDiscussao.objects.create(
        categoria=categoria,
        titulo="Meu Topico",
        conteudo="c",
        autor=admin_user,
        publico_alvo=0,
    )


def test_categoria_list_view_org_filter(client, admin_user, categoria, categoria_outro):
    client.force_login(admin_user)
    url = reverse("discussao:categorias")
    resp = client.get(url)
    assert resp.status_code == 200
    assert list(resp.context["categorias"]) == [categoria]


def test_categoria_list_view_root_sees_all(client, root_user, categoria, categoria_outro):
    client.force_login(root_user)
    resp = client.get(reverse("discussao:categorias"))
    assert resp.status_code == 200
    assert set(resp.context["categorias"]) == {categoria, categoria_outro}


def test_topico_list_view(client, admin_user, categoria, topico):
    client.force_login(admin_user)
    resp = client.get(reverse("discussao:topicos", args=[categoria.slug]))
    assert resp.status_code == 200
    assert list(resp.context["topicos"]) == [topico]


def test_topico_detail_view_increments(client, admin_user, categoria, topico):
    client.force_login(admin_user)
    resp = client.get(reverse("discussao:topico_detalhe", args=[categoria.slug, topico.slug]))
    assert resp.status_code == 200
    topico.refresh_from_db()
    assert topico.numero_visualizacoes == 1
    assert isinstance(resp.context["resposta_form"], RespostaDiscussaoForm)


def test_topico_create_permissions(client, associado_user, categoria):
    client.force_login(associado_user)
    url = reverse("discussao:topico_criar", args=[categoria.slug])
    resp = client.get(url)
    assert resp.status_code == 200


def test_topico_create_success(client, admin_user, categoria):
    client.force_login(admin_user)
    url = reverse("discussao:topico_criar", args=[categoria.slug])
    data = {
        "categoria": categoria.pk,
        "titulo": "Novo",
        "conteudo": "c",
        "publico_alvo": 0,
    }
    resp = client.post(url, data=data)
    assert resp.status_code == 302
    t = TopicoDiscussao.objects.get(titulo="Novo")
    assert t.autor == admin_user and t.categoria == categoria


def test_topico_create_invalid_nucleo(client, admin_user, categoria, nucleo):
    cat = CategoriaDiscussao.objects.create(nome="N", organizacao=categoria.organizacao, nucleo=nucleo)
    outro = Nucleo.objects.create(nome="Outro", slug="outro", organizacao=categoria.organizacao)
    client.force_login(admin_user)
    url = reverse("discussao:topico_criar", args=[cat.slug])
    resp = client.post(
        url,
        data={
            "categoria": cat.pk,
            "titulo": "X",
            "conteudo": "c",
            "publico_alvo": 0,
            "nucleo": outro.pk,
        },
    )
    assert resp.status_code == 200
    assert resp.context["form"].errors


def test_categoria_crud(client, admin_user, organizacao):
    client.force_login(admin_user)
    resp = client.post(
        reverse("discussao:categoria_criar"),
        {"nome": "Nova", "descricao": "", "organizacao": organizacao.pk},
    )
    assert resp.status_code == 302
    cat = CategoriaDiscussao.objects.get(nome="Nova")

    resp = client.post(
        reverse("discussao:categoria_editar", args=[cat.slug]),
        {"nome": "Editada", "descricao": "", "organizacao": organizacao.pk},
    )
    assert resp.status_code == 302
    cat.refresh_from_db()
    assert cat.nome == "Editada"

    resp = client.post(reverse("discussao:categoria_remover", args=[cat.slug]))
    assert resp.status_code == 302
    assert not CategoriaDiscussao.objects.filter(pk=cat.pk).exists()


def test_topico_update_permission(client, admin_user, associado_user, categoria, topico):
    client.force_login(associado_user)
    url = reverse("discussao:topico_editar", args=[categoria.slug, topico.slug])
    resp = client.get(url)
    assert resp.status_code == 403

    client.force_login(admin_user)
    resp2 = client.post(url, {"categoria": categoria.pk, "titulo": "Edit", "conteudo": "c", "publico_alvo": 0})
    assert resp2.status_code == 302
    topico.refresh_from_db()
    assert topico.titulo == "Edit"


def test_topico_delete_view(client, admin_user, associado_user, categoria, topico):
    client.force_login(associado_user)
    resp = client.post(reverse("discussao:topico_remover", args=[categoria.slug, topico.slug]))
    assert resp.status_code == 403
    assert TopicoDiscussao.objects.filter(pk=topico.pk).exists()

    client.force_login(admin_user)
    resp2 = client.post(reverse("discussao:topico_remover", args=[categoria.slug, topico.slug]))
    assert resp2.status_code == 302
    assert not TopicoDiscussao.objects.filter(pk=topico.pk).exists()


def test_resposta_create(client, nucleado_user, categoria, topico):
    client.force_login(nucleado_user)
    url = reverse("discussao:resposta_criar", args=[categoria.slug, topico.slug])
    resp = client.post(url, {"conteudo": "Oi"})
    assert resp.status_code == 302
    r = RespostaDiscussao.objects.get(topico=topico)
    assert r.autor == nucleado_user


def test_resposta_create_reply(client, nucleado_user, categoria, topico):
    parent = RespostaDiscussao.objects.create(topico=topico, autor=nucleado_user, conteudo="p")
    client.force_login(nucleado_user)
    url = reverse("discussao:resposta_criar", args=[categoria.slug, topico.slug])
    resp = client.post(url, {"conteudo": "filho", "reply_to": parent.id})
    assert resp.status_code == 302
    child = RespostaDiscussao.objects.get(reply_to=parent)
    assert child.topico == topico


def test_resposta_update(client, nucleado_user, categoria, topico):
    r = RespostaDiscussao.objects.create(topico=topico, autor=nucleado_user, conteudo="a")
    client.force_login(nucleado_user)
    url = reverse("discussao:resposta_editar", args=[r.id])
    resp = client.post(url, {"conteudo": "b"})
    assert resp.status_code == 302
    r.refresh_from_db()
    assert r.conteudo == "b" and r.editado


def test_interacao_view_toggle(client, nucleado_user, categoria, topico):
    client.force_login(nucleado_user)
    ct = ContentType.objects.get_for_model(topico)
    url = reverse("discussao:interacao", args=[ct.id, topico.id, "like"])
    client.post(url)
    assert InteracaoDiscussao.objects.filter(user=nucleado_user, object_id=topico.id).exists()
    client.post(url)
    assert not InteracaoDiscussao.objects.filter(user=nucleado_user, object_id=topico.id).exists()
    url2 = reverse("discussao:interacao", args=[ct.id, topico.id, "dislike"])
    client.post(url)
    client.post(url2)
    obj = InteracaoDiscussao.objects.get(user=nucleado_user, object_id=topico.id)
    assert obj.tipo == "dislike"


def test_topico_mark_resolved(client, admin_user, categoria, topico, nucleado_user):
    resp = RespostaDiscussao.objects.create(topico=topico, autor=nucleado_user, conteudo="r")
    client.force_login(admin_user)
    url = reverse("discussao:topico_resolver", args=[categoria.slug, topico.slug])
    resp_http = client.post(url, {"melhor_resposta": resp.id})
    assert resp_http.status_code == 302
    topico.refresh_from_db()
    assert topico.status == "fechado" and topico.melhor_resposta == resp


def test_topico_search(client, admin_user, categoria):
    TopicoDiscussao.objects.create(
        categoria=categoria, titulo="Teste A", conteudo="abc", autor=admin_user, publico_alvo=0
    )
    TopicoDiscussao.objects.create(
        categoria=categoria, titulo="Outro", conteudo="def", autor=admin_user, publico_alvo=0
    )
    client.force_login(admin_user)
    url = reverse("discussao:topicos", args=[categoria.slug]) + "?q=Teste"
    resp = client.get(url)
    expected = TopicoDiscussao.objects.get(titulo="Teste A")
    assert list(resp.context["topicos"]) == [expected]


def test_interacao_requires_login(client, categoria, topico):
    ct = ContentType.objects.get_for_model(topico)
    resp = client.post(reverse("discussao:interacao", args=[ct.id, topico.id, "like"]))
    assert resp.status_code == 302
    assert "/accounts/login" in resp.headers["Location"]
