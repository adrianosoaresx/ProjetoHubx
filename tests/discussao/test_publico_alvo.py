import pytest
from django.urls import reverse
from django.http import Http404
from rest_framework.test import APIClient
from django.core.cache import cache

from discussao.models import TopicoDiscussao
from discussao.views import TopicoListView, TopicoDetailView

pytestmark = pytest.mark.django_db


@pytest.fixture
def api_client():
    return APIClient()


@pytest.mark.parametrize(
    "publico, permitido, negado",
    [
        (0, "associado_user", None),
        (1, "nucleado_user", "associado_user"),
        (3, "coordenador_user", "nucleado_user"),
        (4, "associado_user", "nucleado_user"),
    ],
)
def test_views_respeitam_publico_alvo(request, categoria, admin_user, publico, permitido, negado):
    topico = TopicoDiscussao.objects.create(
        categoria=categoria,
        titulo="T",
        conteudo="c",
        autor=admin_user,
        publico_alvo=publico,
    )
    rf = pytest.importorskip('django.test').RequestFactory()

    user = request.getfixturevalue(permitido)
    req = rf.get('/dummy')
    req.user = user
    view = TopicoListView()
    view.request = req
    view.kwargs = {'categoria_slug': categoria.slug}
    view.categoria = categoria
    assert topico in list(view.get_queryset())

    detail_view = TopicoDetailView()
    detail_view.request = req
    detail_view.kwargs = {'categoria_slug': categoria.slug, 'topico_slug': topico.slug}
    assert detail_view.get_object() == topico

    if negado:
        denied_user = request.getfixturevalue(negado)
        req.user = denied_user
        assert topico not in list(view.get_queryset())
        with pytest.raises(Http404):
            detail_view.request = req
            detail_view.get_object()


@pytest.mark.parametrize(
    "publico, permitido, negado",
    [
        (0, "associado_user", None),
        (1, "nucleado_user", "associado_user"),
        (3, "coordenador_user", "nucleado_user"),
        (4, "associado_user", "nucleado_user"),
    ],
)
def test_api_respeita_publico_alvo(api_client, request, categoria, admin_user, publico, permitido, negado):
    cache.clear()
    topico = TopicoDiscussao.objects.create(
        categoria=categoria,
        titulo="T",
        conteudo="c",
        autor=admin_user,
        publico_alvo=publico,
    )
    list_url = reverse("discussao_api:topico-list")
    detail_url = reverse("discussao_api:topico-detail", args=[topico.pk])

    user = request.getfixturevalue(permitido)
    api_client.force_authenticate(user)
    resp = api_client.get(list_url)
    ids = [item["id"] for item in resp.json()]
    assert topico.id in ids
    assert api_client.get(detail_url).status_code == 200

    if negado:
        denied_user = request.getfixturevalue(negado)
        cache.clear()
        api_client.force_authenticate(denied_user)
        resp2 = api_client.get(list_url)
        ids2 = [item["id"] for item in resp2.json()]
        assert topico.id not in ids2
        assert api_client.get(detail_url).status_code in {403, 404}
