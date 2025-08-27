import pytest
from django.contrib.contenttypes.models import ContentType
from django.contrib.messages import get_messages
from django.http import HttpResponse
from django.test import RequestFactory
from django.urls import reverse
from django.template import Context, Template
from freezegun import freeze_time

from discussao.forms import RespostaDiscussaoForm
from discussao.models import (
    CategoriaDiscussao,
    InteracaoDiscussao,
    RespostaDiscussao,
    Tag,
    TopicoDiscussao,
)
from discussao.views import TopicoMarkResolvedView, TopicoDetailView, TopicoListView
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


def test_categoria_list_view_root_denied(client, root_user, categoria):
    client.force_login(root_user)
    resp = client.get(reverse("discussao:categorias"))
    assert resp.status_code == 403


def test_topico_list_view(client, admin_user, categoria, topico):
    client.force_login(admin_user)
    resp = client.get(reverse("discussao:topicos", args=[categoria.slug]))
    assert resp.status_code == 200
    assert list(resp.context["topicos"]) == [topico]


def test_topico_list_view_filters_by_multiple_tags(admin_user, categoria):
    tag1 = Tag.objects.create(nome="tag1")
    tag2 = Tag.objects.create(nome="tag2")
    t1 = TopicoDiscussao.objects.create(
        categoria=categoria,
        titulo="T1",
        conteudo="c",
        autor=admin_user,
        publico_alvo=0,
    )
    t1.tags.add(tag1, tag2)
    t2 = TopicoDiscussao.objects.create(
        categoria=categoria,
        titulo="T2",
        conteudo="c",
        autor=admin_user,
        publico_alvo=0,
    )
    t2.tags.add(tag1)
    rf = RequestFactory()
    request = rf.get("/dummy", {"tags": [tag1.nome, tag2.nome]})
    request.user = admin_user
    response = TopicoListView.as_view()(request, categoria_slug=categoria.slug)
    assert list(response.context_data["topicos"]) == [t1]


def test_topico_list_prefetches_tags(django_assert_num_queries, rf, nucleado_user, categoria):
    tag1 = Tag.objects.create(nome="t1")
    tag2 = Tag.objects.create(nome="t2")
    t1 = TopicoDiscussao.objects.create(
        categoria=categoria,
        titulo="T1",
        conteudo="c",
        autor=nucleado_user,
        publico_alvo=0,
    )
    t1.tags.add(tag1, tag2)
    t2 = TopicoDiscussao.objects.create(
        categoria=categoria,
        titulo="T2",
        conteudo="c",
        autor=nucleado_user,
        publico_alvo=0,
    )
    t2.tags.add(tag1)

    request = rf.get("/")
    request.user = nucleado_user
    view = TopicoListView()
    view.request = request
    view.categoria = categoria

    topicos = list(view.get_queryset())
    with django_assert_num_queries(0):
        for topico in topicos:
            list(topico.tags.all())


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
    assert CategoriaDiscussao.all_objects.filter(pk=cat.pk).exists()


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
    assert TopicoDiscussao.all_objects.filter(pk=topico.pk).exists()


def test_topico_delete_view_rejects_late_deletion(client, associado_user, categoria):
    with freeze_time("2025-07-10 12:00:00"):
        t = TopicoDiscussao.objects.create(
            categoria=categoria,
            titulo="X",
            conteudo="c",
            autor=associado_user,
            publico_alvo=0,
        )
    client.force_login(associado_user)
    url = reverse("discussao:topico_remover", args=[categoria.slug, t.slug])
    with freeze_time("2025-07-10 12:16:00"):
        resp = client.post(url)
    assert resp.status_code == 403
    assert TopicoDiscussao.objects.filter(pk=t.pk).exists()


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


def test_resposta_delete_view_rejects_late_deletion(client, associado_user, categoria):
    with freeze_time("2025-07-10 12:00:00"):
        t = TopicoDiscussao.objects.create(
            categoria=categoria,
            titulo="T",
            conteudo="c",
            autor=associado_user,
            publico_alvo=0,
        )
        r = RespostaDiscussao.objects.create(topico=t, autor=associado_user, conteudo="r")
    client.force_login(associado_user)
    url = reverse("discussao:delete_comment", args=[r.pk])
    with freeze_time("2025-07-10 12:16:00"):
        resp = client.post(url)
    assert resp.status_code == 403
    assert RespostaDiscussao.objects.filter(pk=r.pk).exists()


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


def test_interacao_view_returns_score(client, nucleado_user, categoria, topico):
    client.force_login(nucleado_user)
    ct = ContentType.objects.get_for_model(topico)
    url = reverse("interacao", args=[ct.id, topico.id, "like"], urlconf="discussao.urls")
    resp = client.post("/discussao" + url)
    assert resp.status_code == 200
    data = resp.json()
    assert data["score"] == 1 and data["num_votos"] == 1


def test_interacao_view_invalid_action(client, nucleado_user, categoria, topico):
    client.force_login(nucleado_user)
    ct = ContentType.objects.get_for_model(topico)
    url = reverse("discussao:interacao", args=[ct.id, topico.id, "foo"])
    resp = client.post(url)
    assert resp.status_code == 400
    assert not InteracaoDiscussao.objects.exists()


def test_interacao_view_rejects_invalid_content_type(client, nucleado_user, categoria):
    client.force_login(nucleado_user)
    ct = ContentType.objects.get_for_model(categoria)
    url = reverse("discussao:interacao", args=[ct.id, categoria.id, "like"])
    resp = client.post(url)
    assert resp.status_code == 400
    assert not InteracaoDiscussao.objects.exists()


def test_topico_detail_includes_num_votos(rf, nucleado_user, categoria, topico):
    RespostaDiscussao.objects.create(topico=topico, autor=nucleado_user, conteudo="r")
    request = rf.get("/")
    request.user = nucleado_user
    view = TopicoDetailView()
    view.request = request
    view.kwargs = {"categoria_slug": categoria.slug, "topico_slug": topico.slug}
    obj = view.get_object()
    view.object = obj
    context = view.get_context_data(object=obj)
    assert context["topico"].num_votos == 0
    comentario = context["comentarios"][0]
    assert comentario.num_votos == 0


def test_topico_detail_sets_user_recursively(rf, nucleado_user, categoria, topico):
    r1 = RespostaDiscussao.objects.create(topico=topico, autor=nucleado_user, conteudo="r1")
    RespostaDiscussao.objects.create(topico=topico, autor=nucleado_user, conteudo="r2", reply_to=r1)
    request = rf.get("/")
    request.user = nucleado_user
    view = TopicoDetailView()
    view.request = request
    view.kwargs = {"categoria_slug": categoria.slug, "topico_slug": topico.slug}
    obj = view.get_object()
    view.object = obj
    context = view.get_context_data(object=obj)
    comentario = context["comentarios"][0]
    assert comentario._user == nucleado_user
    assert comentario._obj._user == nucleado_user
    assert comentario.pode_editar
    filho = comentario.respostas_filhas[0]
    assert filho._user == nucleado_user
    assert filho._obj._user == nucleado_user
    assert filho.pode_editar


def test_topico_detail_shows_edit_links_for_author(rf, nucleado_user, categoria, topico):
    r1 = RespostaDiscussao.objects.create(topico=topico, autor=nucleado_user, conteudo="r1")
    RespostaDiscussao.objects.create(topico=topico, autor=nucleado_user, conteudo="r2", reply_to=r1)
    request = rf.get("/")
    request.user = nucleado_user
    view = TopicoDetailView()
    view.request = request
    view.kwargs = {"categoria_slug": categoria.slug, "topico_slug": topico.slug}
    obj = view.get_object()
    view.object = obj
    context = view.get_context_data(object=obj)
    comentario = context["comentarios"][0]
    child = comentario.respostas_filhas[0]

    tpl = Template("""
    {% if comentario.pode_editar %}EDIT{% endif %}
    {% if comentario.pode_editar or user_type in allowed %}DEL{% endif %}
    """)
    ctx = {"user_type": nucleado_user.get_tipo_usuario, "allowed": ["admin", "coordenador", "root"]}
    root_render = tpl.render(Context({"comentario": comentario, **ctx}))
    child_render = tpl.render(Context({"comentario": child, **ctx}))
    assert "EDIT" in root_render and "DEL" in root_render
    assert "EDIT" in child_render and "DEL" in child_render


def test_topico_list_includes_num_votos(rf, nucleado_user, categoria, topico):
    request = rf.get("/")
    request.user = nucleado_user
    view = TopicoListView()
    view.request = request
    view.categoria = categoria
    view.kwargs = {}
    qs = view.get_queryset()
    context = view.get_context_data(object_list=qs)
    topico_ctx = context["topicos"][0]
    assert topico_ctx.num_votos == 0


def test_topico_mark_resolved(client, admin_user, categoria, topico, nucleado_user):
    resp = RespostaDiscussao.objects.create(topico=topico, autor=nucleado_user, conteudo="r")
    client.force_login(admin_user)
    url = reverse("discussao:topico_resolver", args=[categoria.slug, topico.slug])
    resp_http = client.post(url, {"melhor_resposta": resp.id})
    assert resp_http.status_code == 302
    topico.refresh_from_db()
    assert topico.melhor_resposta == resp


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


def test_topico_search_no_duplicates(rf, admin_user, nucleado_user, categoria):
    topico = TopicoDiscussao.objects.create(
        categoria=categoria, titulo="T", conteudo="c", autor=admin_user, publico_alvo=0
    )
    RespostaDiscussao.objects.create(topico=topico, autor=nucleado_user, conteudo="foo")
    RespostaDiscussao.objects.create(topico=topico, autor=nucleado_user, conteudo="foo again")

    request = rf.get("/dummy", {"q": "foo"})
    request.user = admin_user
    response = TopicoListView.as_view()(request, categoria_slug=categoria.slug)
    assert list(response.context_data["topicos"]) == [topico]


def test_resposta_edicao_limite(client, nucleado_user, categoria, topico):
    with freeze_time("2025-07-10 12:00:00"):
        r = RespostaDiscussao.objects.create(topico=topico, autor=nucleado_user, conteudo="a")
    client.force_login(nucleado_user)
    url = reverse("discussao:resposta_editar", args=[r.id])
    with freeze_time("2025-07-10 12:16:00"):
        resp = client.post(url, {"conteudo": "b"})
    assert resp.status_code == 302
    assert resp.headers["Location"].endswith(
        reverse("discussao:topico_detalhe", args=[categoria.slug, topico.slug])
    )
    msgs = [str(m) for m in get_messages(resp.wsgi_request)]
    assert any("Prazo de edição expirado" in m for m in msgs)
    r.refresh_from_db()
    assert r.conteudo == "a"


def test_topico_edicao_limite(client, associado_user, categoria):
    with freeze_time("2025-07-10 12:00:00"):
        t = TopicoDiscussao.objects.create(
            categoria=categoria, titulo="T", conteudo="c", autor=associado_user, publico_alvo=0
        )
    client.force_login(associado_user)
    url = reverse("discussao:topico_editar", args=[categoria.slug, t.slug])
    data = {"categoria": categoria.pk, "titulo": "Edit", "conteudo": "c", "publico_alvo": 0}
    with freeze_time("2025-07-10 12:16:00"):
        resp = client.post(url, data=data)
    assert resp.status_code == 302
    assert resp.headers["Location"].endswith(
        reverse("discussao:topico_detalhe", args=[categoria.slug, t.slug])
    )
    msgs = [str(m) for m in get_messages(resp.wsgi_request)]
    assert any("Prazo de edição expirado" in m for m in msgs)
    t.refresh_from_db()
    assert t.titulo == "T"


def test_toggle_fechado(client, nucleado_user, admin_user, categoria):
    top = TopicoDiscussao.objects.create(
        categoria=categoria, titulo="T", conteudo="c", autor=nucleado_user, publico_alvo=0
    )
    url = reverse("discussao:topico_toggle_fechado", args=[categoria.slug, top.slug])
    client.force_login(nucleado_user)
    resp = client.post(url)
    assert resp.status_code == 302
    top.refresh_from_db()
    assert top.fechado is True
    resp2 = client.post(url)
    assert resp2.status_code == 403
    client.force_login(admin_user)
    resp3 = client.post(url)
    assert resp3.status_code == 302
    top.refresh_from_db()
    assert top.fechado is False


def test_interacao_requires_login(client, categoria, topico):
    ct = ContentType.objects.get_for_model(topico)
    resp = client.post(reverse("discussao:interacao", args=[ct.id, topico.id, "like"]))
    assert resp.status_code == 302
    assert "/accounts/login" in resp.headers["Location"]


def test_topico_mark_resolved_view_triggers_tasks(
    associado_user, nucleado_user, categoria, monkeypatch
):
    topico = TopicoDiscussao.objects.create(
        categoria=categoria, titulo="T", conteudo="c", autor=associado_user, publico_alvo=0
    )
    resp = RespostaDiscussao.objects.create(topico=topico, autor=nucleado_user, conteudo="r")
    called: dict[str, int] = {}

    def fake_best(resposta_id: int) -> None:
        called["resposta"] = resposta_id

    def fake_topico(topico_id: int) -> None:
        called["topico"] = topico_id

    monkeypatch.setattr("discussao.tasks.notificar_melhor_resposta.delay", fake_best)
    monkeypatch.setattr("discussao.tasks.notificar_topico_resolvido.delay", fake_topico)
    rf = RequestFactory()
    request = rf.post("/dummy", {"melhor_resposta": resp.id})
    request.user = associado_user
    monkeypatch.setattr("django.contrib.messages.api.add_message", lambda *a, **k: None)
    monkeypatch.setattr("discussao.views.redirect", lambda *a, **k: HttpResponse("ok"))
    TopicoMarkResolvedView.as_view()(request, categoria_slug=categoria.slug, topico_slug=topico.slug)
    assert called["resposta"] == resp.id and called["topico"] == topico.id
