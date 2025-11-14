from __future__ import annotations

import pytest
from django import forms
from django.test import override_settings
from django.urls import reverse

from configuracoes.views import ConfiguracoesView
from configuracoes.forms import ConfiguracaoContaForm
from configuracoes.services import get_configuracao_conta
from pathlib import Path

from django.contrib.auth.forms import PasswordChangeForm
from notificacoes.models import NotificationTemplate, Canal

pytestmark = pytest.mark.django_db


@override_settings(ROOT_URLCONF="tests.configuracoes.urls")
def test_view_get_autenticado(admin_client):
    resp = admin_client.get(reverse("configuracoes:configuracoes"))
    assert resp.status_code == 200
    assert isinstance(resp.context["seguranca_form"], PasswordChangeForm)
    assert "preferencias_form" in resp.context
    assert "configuracoes/configuracao.html" in [t.name for t in resp.templates]


@override_settings(ROOT_URLCONF="tests.configuracoes.urls")
def test_configuracoes_non_htmx_renders_full_template(admin_client):
    response = admin_client.get(reverse("configuracoes:configuracoes"))

    assert response.status_code == 200
    template_names = [template.name for template in response.templates if template.name]
    assert template_names[0] == "configuracoes/configuracao.html"


@override_settings(ROOT_URLCONF="tests.configuracoes.urls")
def test_admin_user_can_view_notification_templates(admin_client):
    NotificationTemplate.objects.create(
        codigo="boas-vindas",
        assunto="Assunto",
        corpo="Corpo",
        canal=Canal.EMAIL,
    )

    response = admin_client.get(reverse("configuracoes:configuracoes"))

    assert response.status_code == 200
    assert response.context["can_view_notification_templates"] is True
    content = response.content.decode()
    assert "Você não possui permissão para visualizar os templates de notificação." not in content



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


@override_settings(ROOT_URLCONF="tests.configuracoes.urls")
def test_post_preferencias_from_seguranca_route_only_validates_preferencias_form(admin_client, admin_user):
    configuracao = get_configuracao_conta(admin_user)
    form = ConfiguracaoContaForm(instance=configuracao)
    data = {}
    for field_name, field in form.fields.items():
        value = form.initial.get(field_name)
        if isinstance(field.widget, forms.CheckboxInput):
            data[field_name] = "on" if value else ""
        elif field_name in {"hora_notificacao_diaria", "hora_notificacao_semanal"} and value:
            data[field_name] = value.strftime("%H:%M")
        else:
            data[field_name] = value if value is not None else ""
    data["section"] = "preferencias"

    response = admin_client.post(reverse("configuracoes:configuracoes_seguranca"), data)

    assert response.status_code == 200
    preferencias_form = response.context["preferencias_form"]
    seguranca_form = response.context["seguranca_form"]
    assert preferencias_form.is_bound
    assert preferencias_form.is_valid()
    assert not preferencias_form.errors
    assert not seguranca_form.is_bound
    assert "old_password" not in seguranca_form.errors


@override_settings(ROOT_URLCONF="tests.configuracoes.urls")
def test_post_seguranca_from_preferencias_route_only_validates_password_form(admin_client):
    payload = {
        "section": "seguranca",
        "old_password": "pass",
        "new_password1": "NovaSenhaSegura123!",
        "new_password2": "NovaSenhaSegura123!",
    }

    response = admin_client.post(reverse("configuracoes:configuracoes_preferencias"), payload)

    assert response.status_code == 200
    seguranca_form = response.context["seguranca_form"]
    preferencias_form = response.context["preferencias_form"]
    assert seguranca_form.is_bound
    assert seguranca_form.is_valid()
    assert not seguranca_form.errors
    assert not preferencias_form.is_bound
    assert not preferencias_form.errors


