from __future__ import annotations

import pytest
from django.contrib.auth.forms import PasswordChangeForm
from django.test import override_settings
from django.urls import reverse

from accounts.forms import InformacoesPessoaisForm, RedesSociaisForm
from configuracoes.forms import ConfiguracaoContaForm

pytestmark = pytest.mark.django_db


@override_settings(ROOT_URLCONF="tests.configuracoes.urls")
def test_view_get_autenticado(admin_client):
    resp = admin_client.get(reverse("configuracoes"))
    assert resp.status_code == 200
    assert isinstance(resp.context["informacoes_form"], InformacoesPessoaisForm)
    assert isinstance(resp.context["seguranca_form"], PasswordChangeForm)
    assert isinstance(resp.context["redes_form"], RedesSociaisForm)
    assert isinstance(resp.context["preferencias_form"], ConfiguracaoContaForm)
    assert "configuracoes/configuracoes.html" in [t.name for t in resp.templates]


@override_settings(ROOT_URLCONF="tests.configuracoes.urls")
def test_view_get_redirect_nao_autenticado(client):
    resp = client.get(reverse("configuracoes"))
    assert resp.status_code == 302
    assert "/accounts/login" in resp.headers["Location"]


@override_settings(ROOT_URLCONF="tests.configuracoes.urls")
def test_view_post_atualiza_preferencias(admin_client, admin_user):
    url = reverse("configuracoes") + "?tab=preferencias"
    data = {
        "receber_notificacoes_email": False,
        "frequencia_notificacoes_email": "diaria",
        "receber_notificacoes_whatsapp": True,
        "frequencia_notificacoes_whatsapp": "semanal",
        "idioma": "pt-BR",
        "tema": "escuro",
        "tab": "preferencias",
    }
    resp = admin_client.post(url, data)
    assert resp.status_code == 200
    admin_user.configuracao.refresh_from_db()
    assert admin_user.configuracao.tema == "escuro"
    assert admin_user.configuracao.receber_notificacoes_email is False
    assert resp.cookies["tema"].value == "escuro"
