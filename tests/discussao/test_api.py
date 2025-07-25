import pytest
from django.urls import reverse
from freezegun import freeze_time
from rest_framework.test import APIClient

from discussao.models import RespostaDiscussao, Tag, TopicoDiscussao

pytestmark = pytest.mark.django_db


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


def test_marcar_melhor_resposta_permission(api_client, categoria, admin_user, associado_user):
    topico = create_topico(categoria, associado_user)
    resp = RespostaDiscussao.objects.create(topico=topico, autor=admin_user, conteudo="r")
    url = reverse("discussao_api:topico-marcar-melhor-resposta", args=[topico.pk])

    api_client.force_authenticate(user=associado_user)
    response = api_client.post(url, {"resposta_id": resp.id})
    assert response.status_code == 200
    topico.refresh_from_db()
    assert topico.melhor_resposta == resp

    api_client.force_authenticate(user=admin_user)
    resp2 = RespostaDiscussao.objects.create(topico=topico, autor=associado_user, conteudo="x")
    response2 = api_client.post(url, {"resposta_id": resp2.id})
    assert response2.status_code == 200
    topico.refresh_from_db()
    assert topico.melhor_resposta == resp2


def test_edicao_apos_limite(api_client, categoria, associado_user, admin_user):
    with freeze_time("2025-07-10 12:00:00"):
        topico = create_topico(categoria, associado_user)
    api_client.force_authenticate(user=associado_user)
    url = reverse("discussao_api:topico-detail", args=[topico.pk])
    with freeze_time("2025-07-10 12:16:00"):
        resp = api_client.patch(url, {"titulo": "Novo"})
    assert resp.status_code == 403
    api_client.force_authenticate(user=admin_user)
    with freeze_time("2025-07-10 12:16:00"):
        resp2 = api_client.patch(url, {"titulo": "Novo"})
    assert resp2.status_code == 200
    topico.refresh_from_db()
    assert topico.titulo == "Novo"


def test_fechar_e_reabrir_topico(api_client, categoria, associado_user):
    topico = create_topico(categoria, associado_user)
    api_client.force_authenticate(user=associado_user)
    close_url = reverse("discussao_api:topico-fechar", args=[topico.pk])
    resp = api_client.patch(close_url)
    assert resp.status_code == 200
    topico.refresh_from_db()
    assert topico.status == "fechado"
    # tentar responder deve falhar
    resp_url = reverse("discussao_api:resposta-list")
    response = api_client.post(resp_url, {"topico": topico.id, "conteudo": "c"})
    assert response.status_code == 403
    reopen_url = reverse("discussao_api:topico-reabrir", args=[topico.pk])
    resp2 = api_client.patch(reopen_url)
    assert resp2.status_code == 200
    topico.refresh_from_db()
    assert topico.status == "aberto"
    response2 = api_client.post(resp_url, {"topico": topico.id, "conteudo": "c"})
    assert response2.status_code == 201


def test_filtro_por_tags(api_client, categoria, associado_user):
    tag1 = Tag.objects.create(nome="django")
    tag2 = Tag.objects.create(nome="backend")
    topico1 = create_topico(categoria, associado_user, title="T1")
    topico1.tags.add(tag1)
    topico2 = create_topico(categoria, associado_user, title="T2")
    topico2.tags.add(tag2)
    api_client.force_authenticate(user=associado_user)
    url = reverse("discussao_api:topico-list") + "?tags=django"
    resp = api_client.get(url)
    ids = [t["id"] for t in resp.data]
    assert topico1.id in ids and topico2.id not in ids
