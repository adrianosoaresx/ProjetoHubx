import sys
import types

import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from discussao.models import TopicoDiscussao


pytestmark = pytest.mark.django_db


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def topico(categoria, associado_user):
    return TopicoDiscussao.objects.create(
        categoria=categoria,
        titulo="T",
        conteudo="c",
        autor=associado_user,
        publico_alvo=0,
    )


def test_criar_reuniao_dispara_agenda(api_client, topico, monkeypatch, settings):
    chamada = {}

    def fake_criar(*args, **kwargs):
        chamada["ok"] = True

    monkeypatch.setitem(sys.modules, "agenda.services", types.SimpleNamespace(criar_reuniao=fake_criar))
    settings.DISCUSSAO_AGENDA_BRIDGE_ENABLED = True

    api_client.force_authenticate(user=topico.autor)
    url = reverse("discussao_api:topico-criar-reuniao", args=[topico.pk])
    resp = api_client.post(
        url,
        {
            "data_inicio": "2025-01-01T12:00:00Z",
            "data_fim": "2025-01-01T13:00:00Z",
            "participantes": [],
        },
    )
    assert resp.status_code == 204
    assert chamada.get("ok") is True


@pytest.mark.xfail(reason="Agenda bridge desativado")
def test_criar_reuniao_flag_desligada(api_client, topico, monkeypatch):
    chamada = {}

    def fake_criar(*args, **kwargs):
        chamada["ok"] = True

    monkeypatch.setitem(sys.modules, "agenda.services", types.SimpleNamespace(criar_reuniao=fake_criar))

    api_client.force_authenticate(user=topico.autor)
    url = reverse("discussao_api:topico-criar-reuniao", args=[topico.pk])
    api_client.post(
        url,
        {
            "data_inicio": "2025-01-01T12:00:00Z",
            "data_fim": "2025-01-01T13:00:00Z",
            "participantes": [],
        },
    )
    assert chamada.get("ok")

