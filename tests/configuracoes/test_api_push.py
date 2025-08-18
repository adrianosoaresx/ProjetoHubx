import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from notificacoes.models import Canal

pytestmark = pytest.mark.django_db


@pytest.fixture
def client(admin_user):
    c = APIClient()
    c.force_authenticate(admin_user)
    return c


def test_disable_push(client, admin_user):
    url = reverse("configuracoes_api:configuracoes-conta")
    resp = client.patch(url, {"receber_notificacoes_push": False})
    assert resp.status_code == 200
    admin_user.configuracao.refresh_from_db()
    assert admin_user.configuracao.receber_notificacoes_push is False


def test_change_push_frequency(client, admin_user):
    url = reverse("configuracoes_api:configuracoes-conta")
    resp = client.patch(url, {"frequencia_notificacoes_push": "diaria"})
    assert resp.status_code == 200
    resp = client.patch(url, {"frequencia_notificacoes_push": "invalida"})
    assert resp.status_code == 400


def test_testar_notificacao_respeita_push(client, admin_user):
    admin_user.configuracao.receber_notificacoes_push = False
    admin_user.configuracao.save(update_fields=["receber_notificacoes_push"])
    resp = client.post(reverse("configuracoes_api:configuracoes-testar"), {"canal": Canal.PUSH})
    assert resp.status_code == 400
    admin_user.configuracao.receber_notificacoes_push = True
    admin_user.configuracao.save(update_fields=["receber_notificacoes_push"])
    resp = client.post(reverse("configuracoes_api:configuracoes-testar"), {"canal": Canal.PUSH})
    assert resp.status_code == 200
