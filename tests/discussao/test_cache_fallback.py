from unittest.mock import patch

import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from discussao.factories import RespostaDiscussaoFactory, TopicoDiscussaoFactory
from discussao.tasks import notificar_nova_resposta


@pytest.mark.django_db
def test_list_view_locmem_cache(admin_user):
    client = APIClient()
    client.force_authenticate(admin_user)
    TopicoDiscussaoFactory.create_batch(2, autor=admin_user)
    resp = client.get(reverse("discussao_api:topico-list"))
    assert resp.status_code == 200


@pytest.mark.django_db
def test_celery_eager_mode():
    resposta = RespostaDiscussaoFactory()
    with patch("discussao.tasks.enviar_para_usuario") as mocked:
        result = notificar_nova_resposta.delay(resposta.id)
        assert result.successful()
        assert mocked.called
