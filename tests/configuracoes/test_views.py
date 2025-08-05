from __future__ import annotations

import pytest
import pytest
from django.test import override_settings
from django.urls import reverse
from pathlib import Path

from accounts.forms import InformacoesPessoaisForm

pytestmark = pytest.mark.django_db


@override_settings(ROOT_URLCONF="tests.configuracoes.urls")
def test_view_get_autenticado(admin_client):
    resp = admin_client.get(reverse("configuracoes"))
    assert resp.status_code == 200
    assert isinstance(resp.context["informacoes_form"], InformacoesPessoaisForm)
    assert "seguranca_form" not in resp.context
    assert "redes_form" not in resp.context
    assert "preferencias_form" not in resp.context
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
        "hora_notificacao_diaria": "08:00",
        "hora_notificacao_semanal": "08:00",
        "dia_semana_notificacao": 0,
        "tab": "preferencias",
    }
    resp = admin_client.post(url, data, HTTP_HX_REQUEST="true")
    assert resp.status_code == 200
    admin_user.configuracao.refresh_from_db()
    assert admin_user.configuracao.tema == "escuro"
    assert admin_user.configuracao.receber_notificacoes_email is False
    assert resp.cookies["tema"].value == "escuro"
    assert resp.cookies["django_language"].value == "pt-BR"
    content = resp.content.decode()
    assert 'const tema = "escuro"' in content
    assert "localStorage.setItem('tema', tema)" in content


try:
    import pytest_benchmark  # noqa:F401
    HAS_BENCH = True
except Exception:  # pragma: no cover - dependencia opcional
    HAS_BENCH = False


@override_settings(ROOT_URLCONF="tests.configuracoes.urls")
@pytest.mark.skipif(not HAS_BENCH, reason="pytest-benchmark não instalado")
def test_view_benchmark(admin_client, benchmark):
    url = reverse("configuracoes")

    def fetch():
        return admin_client.get(url)

    resp = benchmark(fetch)
    assert resp.status_code == 200
    stats = benchmark.stats.stats
    data = stats.sorted_data
    p95 = data[int(len(data) * 0.95) - 1]
    assert p95 < 0.1


def test_base_template_localstorage():
    content = Path("templates/base.html").read_text()
    assert "localStorage.setItem('tema'" in content
    assert "localStorage.setItem('idioma'" in content
