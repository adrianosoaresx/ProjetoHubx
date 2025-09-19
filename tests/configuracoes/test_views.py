from __future__ import annotations

import pytest
from django.test import override_settings
from django.urls import reverse

from configuracoes.views import ConfiguracoesView
from pathlib import Path

from django.contrib.auth.forms import PasswordChangeForm

pytestmark = pytest.mark.django_db


@override_settings(ROOT_URLCONF="tests.configuracoes.urls")
def test_view_get_autenticado(admin_client):
    resp = admin_client.get(reverse("configuracoes:configuracoes"))
    assert resp.status_code == 200
    assert isinstance(resp.context["seguranca_form"], PasswordChangeForm)
    assert "preferencias_form" not in resp.context
    assert "configuracoes/configuracao_form.html" in [t.name for t in resp.templates]


@override_settings(ROOT_URLCONF="tests.configuracoes.urls")
def test_configuracoes_non_htmx_renders_full_template(admin_client):
    response = admin_client.get(reverse("configuracoes:configuracoes"))

    assert response.status_code == 200
    template_names = [template.name for template in response.templates if template.name]
    assert template_names[0] == "configuracoes/configuracao_form.html"




@override_settings(ROOT_URLCONF="tests.configuracoes.urls")
def test_view_get_redirect_nao_autenticado(client):
    resp = client.get(reverse("configuracoes:configuracoes"))
    assert resp.status_code == 302
    assert "/accounts/login" in resp.headers["Location"]




# Benchmarks removidos para simplificar a suíte sem dependências extras.


def test_base_template_localstorage():
    content = Path("templates/base.html").read_text()
    assert "localStorage.setItem('tema'" in content
    assert "localStorage.setItem('idioma'" in content


