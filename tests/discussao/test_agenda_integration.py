from unittest.mock import patch

import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from accounts.factories import UserFactory
from discussao.factories import TopicoDiscussaoFactory


@pytest.mark.django_db
def test_agendar_topico_autor(settings):
    settings.FEATURE_DISCUSSAO_AGENDA = True
    user = UserFactory()
    topico = TopicoDiscussaoFactory(autor=user)
    client = APIClient()
    client.force_authenticate(user)
    payload = {
        "titulo": "Reunião",
        "inicio": "2025-01-01T10:00:00+00:00",
        "fim": "2025-01-01T11:00:00+00:00",
        "descricao": "Discussão",
    }
    url = reverse("discussao_api:topico-agendar", args=[topico.id])
    with patch("discussao.api.notificar_agendamento_criado.delay") as mocked:
        resp = client.post(url, payload, format="json")
    assert resp.status_code == 201
    mocked.assert_called_once()


@pytest.mark.django_db
def test_agendar_flag_off(settings):
    settings.FEATURE_DISCUSSAO_AGENDA = False
    user = UserFactory()
    topico = TopicoDiscussaoFactory(autor=user)
    client = APIClient()
    client.force_authenticate(user)
    url = reverse("discussao_api:topico-agendar", args=[topico.id])
    resp = client.post(
        url,
        {"titulo": "x", "inicio": "2025-01-01T10:00:00+00:00", "fim": "2025-01-01T11:00:00+00:00"},
        format="json",
    )
    assert resp.status_code == 403


@pytest.mark.django_db
def test_agendar_sem_permissao(settings):
    settings.FEATURE_DISCUSSAO_AGENDA = True
    autor = UserFactory()
    outro = UserFactory()
    topico = TopicoDiscussaoFactory(autor=autor)
    client = APIClient()
    client.force_authenticate(outro)
    url = reverse("discussao_api:topico-agendar", args=[topico.id])
    resp = client.post(
        url,
        {"titulo": "x", "inicio": "2025-01-01T10:00:00+00:00", "fim": "2025-01-01T11:00:00+00:00"},
        format="json",
    )
    assert resp.status_code == 403
