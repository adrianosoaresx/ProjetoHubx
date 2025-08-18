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


def test_topico_serializer_includes_score(api_client, categoria, associado_user):
    topico = create_topico(categoria, associado_user)
    api_client.force_authenticate(user=associado_user)
    url = reverse("topico-detail", args=[topico.pk], urlconf="discussao.api_urls")
    resp = api_client.get("/api/discussao" + url)
    assert resp.status_code == 200
    assert resp.data["score"] == 0 and resp.data["num_votos"] == 0


def test_resposta_serializer_includes_score(api_client, categoria, associado_user):
    topico = create_topico(categoria, associado_user)
    resposta = RespostaDiscussao.objects.create(
        topico=topico, autor=associado_user, conteudo="r"
    )
    api_client.force_authenticate(user=associado_user)
    url = reverse("resposta-detail", args=[resposta.pk], urlconf="discussao.api_urls")
    resp = api_client.get("/api/discussao" + url)
    assert resp.status_code == 200
    assert resp.data["score"] == 0 and resp.data["num_votos"] == 0


def test_marcar_resolvido_permission(api_client, categoria, admin_user, associado_user):
    topico = create_topico(categoria, associado_user)
    resp = RespostaDiscussao.objects.create(topico=topico, autor=admin_user, conteudo="r")
    url = reverse("discussao_api:topico-marcar-resolvido", args=[topico.pk])

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


def test_fechar_e_reabrir_topico(api_client, categoria, associado_user, admin_user):
    topico = create_topico(categoria, associado_user)
    api_client.force_authenticate(user=associado_user)
    close_url = reverse("discussao_api:topico-fechar", args=[topico.pk])
    resp = api_client.patch(close_url)
    assert resp.status_code == 200
    topico.refresh_from_db()
    assert topico.fechado is True
    # tentar responder deve falhar
    resp_url = reverse("discussao_api:resposta-list")
    response = api_client.post(resp_url, {"topico": topico.id, "conteudo": "c"})
    assert response.status_code == 403
    reopen_url = reverse("discussao_api:topico-reabrir", args=[topico.pk])
    resp2 = api_client.patch(reopen_url)
    assert resp2.status_code == 403
    api_client.force_authenticate(user=admin_user)
    resp3 = api_client.patch(reopen_url)
    assert resp3.status_code == 200
    topico.refresh_from_db()
    assert topico.fechado is False
    response2 = api_client.post(resp_url, {"topico": topico.id, "conteudo": "c"})
    assert response2.status_code == 201


def test_filtro_por_tags(api_client, categoria, associado_user):
    tag1 = Tag.objects.create(nome="django")
    tag2 = Tag.objects.create(nome="backend")
    topico1 = create_topico(categoria, associado_user, title="T1")
    topico1.tags.add(tag1)
    topico2 = create_topico(categoria, associado_user, title="T2")
    topico2.tags.add(tag1, tag2)
    topico3 = create_topico(categoria, associado_user, title="T3")
    topico3.tags.add(tag2)
    api_client.force_authenticate(user=associado_user)
    url = reverse("discussao_api:topico-list") + "?tags=django,backend"
    resp = api_client.get(url)
    ids = {t["id"] for t in resp.data}
    assert ids == {topico2.id}


def test_busca_full_text(api_client, categoria, associado_user):
    topico1 = create_topico(categoria, associado_user, title="Django tips")
    RespostaDiscussao.objects.create(topico=topico1, autor=associado_user, conteudo="Como usar ORM")
    topico2 = create_topico(categoria, associado_user, title="Flask")
    api_client.force_authenticate(user=associado_user)
    url = reverse("discussao_api:topico-list") + "?search=django"
    resp = api_client.get(url)
    ids = {t["id"] for t in resp.data}
    assert topico1.id in ids and topico2.id not in ids


def test_tasks_disparadas(api_client, categoria, associado_user, admin_user, monkeypatch):
    topico = create_topico(categoria, associado_user)
    api_client.force_authenticate(user=admin_user)
    called = {}

    def fake_delay(resposta_id: int) -> None:
        called["resposta"] = resposta_id

    monkeypatch.setattr("discussao.tasks.notificar_nova_resposta.delay", fake_delay)
    url_resp = reverse("discussao_api:resposta-list")
    resp = api_client.post(url_resp, {"topico": topico.id, "conteudo": "oi"})
    assert resp.status_code == 201 and "resposta" in called

    resposta = RespostaDiscussao.objects.get(id=called["resposta"])
    called2 = {}

    def fake_best(resposta_id: int) -> None:
        called2["resposta"] = resposta_id

    monkeypatch.setattr("discussao.tasks.notificar_melhor_resposta.delay", fake_best)
    api_client.force_authenticate(user=associado_user)
    url = reverse("discussao_api:topico-marcar-resolvido", args=[topico.pk])
    resp2 = api_client.post(url, {"resposta_id": resposta.id})
    assert resp2.status_code == 200 and called2["resposta"] == resposta.id
