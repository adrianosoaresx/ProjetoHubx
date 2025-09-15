from __future__ import annotations

import pytest
from bs4 import BeautifulSoup
from django.http import Http404
from django.test import override_settings
from django.urls import reverse
from django.test.client import RequestFactory
from django.contrib.messages.storage.fallback import FallbackStorage

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
def test_configuracoes_htmx_seguranca_returns_partial(admin_client):
    response = admin_client.get(
        reverse("configuracoes:configuracoes"),
        {"tab": "seguranca"},
        HTTP_HX_REQUEST="true",
    )

    assert response.status_code == 200
    template_names = [template.name for template in response.templates if template.name]
    assert template_names[0] == "configuracoes/_partials/seguranca.html"
    assert "configuracoes/configuracao_form.html" not in template_names
    assert "base.html" not in template_names


@override_settings(ROOT_URLCONF="tests.configuracoes.urls")
def test_configuracoes_htmx_preferencias_returns_partial(admin_client):
    response = admin_client.get(
        reverse("configuracoes:configuracoes"),
        {"tab": "preferencias"},
        HTTP_HX_REQUEST="true",
    )

    assert response.status_code == 200
    template_names = [template.name for template in response.templates if template.name]
    assert template_names[0] == "configuracoes/_partials/preferencias.html"
    assert "configuracoes/configuracao_form.html" not in template_names
    assert "base.html" not in template_names


@override_settings(ROOT_URLCONF="tests.configuracoes.urls")
def test_configuracoes_tab_shell_accessible_markup(admin_client):
    response = admin_client.get(reverse("configuracoes:configuracoes"))

    assert response.status_code == 200
    soup = BeautifulSoup(response.content, "html.parser")
    tablist = soup.find("nav", {"role": "tablist"})
    assert tablist is not None

    tabs = tablist.find_all("a", {"role": "tab"})
    assert len(tabs) == 2

    seguranca_tab = next(tab for tab in tabs if "tab=seguranca" in tab.get("href", ""))
    preferencias_tab = next(tab for tab in tabs if "tab=preferencias" in tab.get("href", ""))

    assert seguranca_tab.get("aria-selected") == "true"
    assert seguranca_tab.get("tabindex") == "0"
    assert preferencias_tab.get("aria-selected") == "false"
    assert preferencias_tab.get("tabindex") == "-1"


@override_settings(ROOT_URLCONF="tests.configuracoes.urls")
def test_view_get_redirect_nao_autenticado(client):
    resp = client.get(reverse("configuracoes:configuracoes"))
    assert resp.status_code == 302
    assert "/accounts/login" in resp.headers["Location"]


@override_settings(ROOT_URLCONF="tests.configuracoes.urls")
def test_view_get_redes_redirect(admin_client):
    resp = admin_client.get(reverse("configuracoes:configuracoes") + "?tab=redes")
    assert resp.status_code == 302
    assert resp.headers["Location"] == reverse("accounts:redes_sociais")


@override_settings(ROOT_URLCONF="tests.configuracoes.urls")
def test_view_get_informacoes_redirect(admin_client):
    resp = admin_client.get(reverse("configuracoes:configuracoes") + "?tab=informacoes")
    assert resp.status_code == 302
    assert resp.headers["Location"] == reverse("accounts:informacoes_pessoais")


def test_view_invalid_tab_returns_404(admin_user, rf: RequestFactory):
    request = rf.get("/configuracoes/?tab=invalido")
    request.user = admin_user
    with pytest.raises(Http404):
        ConfiguracoesView.as_view()(request)


def test_view_post_invalid_tab_returns_404(admin_user, rf: RequestFactory):
    request = rf.post("/configuracoes/?tab=invalido", {"tab": "invalido"})
    request.user = admin_user
    with pytest.raises(Http404):
        ConfiguracoesView.as_view()(request)


@override_settings(ROOT_URLCONF="tests.configuracoes.urls")
def test_view_post_atualiza_preferencias(admin_user, rf: RequestFactory, monkeypatch):
    class DummyForm:
        def __init__(self):
            self.instance = type("obj", (), {"tema": "escuro", "idioma": "pt-BR"})()
            self.cleaned_data = {}

        def is_valid(self):
            return True

    def fake_get_form(self, tab, data=None, files=None):  # pragma: no cover - simple
        return DummyForm()

    monkeypatch.setattr(ConfiguracoesView, "get_form", fake_get_form)
    request = rf.post("/configuracoes/?tab=preferencias", {"tab": "preferencias"})
    request.user = admin_user
    request.session = {}
    setattr(request, "_messages", FallbackStorage(request))
    resp = ConfiguracoesView.as_view()(request)
    tema_cookie = resp.cookies["tema"]
    lang_cookie = resp.cookies["django_language"]
    assert tema_cookie["samesite"] == "Lax"
    assert lang_cookie["samesite"] == "Lax"
    assert tema_cookie["secure"] == ""
    assert lang_cookie["secure"] == ""
    assert tema_cookie["httponly"] == ""
    assert lang_cookie["httponly"] == ""


try:
    import pytest_benchmark  # noqa:F401

    HAS_BENCH = True
except Exception:  # pragma: no cover - dependencia opcional
    HAS_BENCH = False


@override_settings(ROOT_URLCONF="tests.configuracoes.urls")
@pytest.mark.skipif(not HAS_BENCH, reason="pytest-benchmark não instalado")
def test_view_benchmark(admin_client, benchmark):
    url = reverse("configuracoes:configuracoes")

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


@override_settings(ROOT_URLCONF="tests.configuracoes.urls")
def test_view_post_preferencias_https_secure_cookies(admin_user, rf: RequestFactory, monkeypatch):
    class DummyForm:
        def __init__(self):
            self.instance = type("obj", (), {"tema": "escuro", "idioma": "pt-BR"})()
            self.cleaned_data = {}

        def is_valid(self):
            return True

    def fake_get_form(self, tab, data=None, files=None):  # pragma: no cover - simple
        return DummyForm()

    monkeypatch.setattr(ConfiguracoesView, "get_form", fake_get_form)
    request = rf.post("/configuracoes/?tab=preferencias", {"tab": "preferencias"}, secure=True)
    request.user = admin_user
    request.session = {}
    setattr(request, "_messages", FallbackStorage(request))
    resp = ConfiguracoesView.as_view()(request)
    assert resp.cookies["tema"]["secure"] is True
    assert resp.cookies["django_language"]["secure"] is True
