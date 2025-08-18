import pytest
from django.contrib.contenttypes.models import ContentType
from django.urls import reverse
from rest_framework.test import APIClient

from discussao.models import Denuncia, TopicoDiscussao


@pytest.fixture
def api_client():
    return APIClient()


def create_topico(categoria, autor, title="T"):
    return TopicoDiscussao.objects.create(
        categoria=categoria,
        titulo=title,
        conteudo="c",
        autor=autor,
        publico_alvo=0,
    )


def test_criar_denuncia(api_client, categoria, admin_user, associado_user):
    topico = create_topico(categoria, admin_user)
    ct = ContentType.objects.get_for_model(TopicoDiscussao)
    api_client.force_authenticate(user=associado_user)
    url = reverse("denuncia-list", urlconf="discussao.api_urls")
    resp = api_client.post(
        "/api/discussao" + url,
        {"content_type_id": ct.id, "object_id": topico.id, "motivo": "spam"},
    )
    assert resp.status_code == 201
    assert resp.data["status"] == Denuncia.Status.PENDENTE
    assert resp.data["log"] is None


def test_aprovar_denuncia(api_client, categoria, admin_user, associado_user):
    topico = create_topico(categoria, admin_user)
    ct = ContentType.objects.get_for_model(TopicoDiscussao)
    api_client.force_authenticate(user=associado_user)
    create_url = reverse("denuncia-list", urlconf="discussao.api_urls")
    resp = api_client.post(
        "/api/discussao" + create_url,
        {"content_type_id": ct.id, "object_id": topico.id, "motivo": "spam"},
    )
    denuncia_id = resp.data["id"]

    api_client.force_authenticate(user=admin_user)
    url = reverse("denuncia-aprovar", args=[denuncia_id], urlconf="discussao.api_urls")
    resp2 = api_client.post("/api/discussao" + url)
    assert resp2.status_code == 200
    assert resp2.data["status"] == Denuncia.Status.REVISADO
    assert resp2.data["log"]["action"] == "approve"


def test_rejeitar_denuncia(api_client, categoria, admin_user, associado_user):
    topico = create_topico(categoria, admin_user)
    ct = ContentType.objects.get_for_model(TopicoDiscussao)
    api_client.force_authenticate(user=associado_user)
    create_url = reverse("denuncia-list", urlconf="discussao.api_urls")
    resp = api_client.post(
        "/api/discussao" + create_url,
        {"content_type_id": ct.id, "object_id": topico.id, "motivo": "spam"},
    )
    denuncia_id = resp.data["id"]

    api_client.force_authenticate(user=admin_user)
    url = reverse("denuncia-rejeitar", args=[denuncia_id], urlconf="discussao.api_urls")
    resp2 = api_client.post("/api/discussao" + url)
    assert resp2.status_code == 200
    assert resp2.data["status"] == Denuncia.Status.REJEITADO
    assert resp2.data["log"]["action"] == "reject"
