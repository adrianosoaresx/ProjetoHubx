from __future__ import annotations

import pytest
from django.test import override_settings
from django.urls import reverse

from configuracoes.forms import ConfiguracaoContaForm

pytestmark = pytest.mark.django_db


@override_settings(ROOT_URLCONF="tests.configuracoes.urls")
def test_view_get_autenticado(admin_client):
    resp = admin_client.get(reverse("configuracoes"))
    assert resp.status_code == 200
    assert isinstance(resp.context["form"], ConfiguracaoContaForm)
    assert "configuracoes/configuracoes.html" in [t.name for t in resp.templates]


@override_settings(ROOT_URLCONF="tests.configuracoes.urls")
def test_view_get_redirect_nao_autenticado(client):
    resp = client.get(reverse("configuracoes"))
    assert resp.status_code == 302
    assert "/accounts/login" in resp.headers["Location"]


@override_settings(ROOT_URLCONF="tests.configuracoes.urls")
def test_view_post_atualiza_configuracao(admin_client, admin_user):
    url = reverse("configuracoes")
    data = {
        "receber_notificacoes_email": False,
        "receber_notificacoes_whatsapp": True,
        "tema_escuro": True,
    }
    resp = admin_client.post(url, data)
    assert resp.status_code == 200
    admin_user.configuracao.refresh_from_db()
    assert admin_user.configuracao.tema_escuro is True
    assert admin_user.configuracao.receber_notificacoes_email is False
    assert admin_user.configuracao.receber_notificacoes_whatsapp is True
    assert resp.context.get("success") is True
