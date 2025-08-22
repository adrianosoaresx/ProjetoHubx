import pytest
from django.urls import reverse
from rest_framework.test import APIClient
from playwright.sync_api import sync_playwright

from accounts.factories import UserFactory
from organizacoes.factories import OrganizacaoFactory
from nucleos.factories import NucleoFactory
from agenda.factories import EventoFactory

pytestmark = pytest.mark.django_db


def test_contextual_scope_selection(live_server):
    user = UserFactory(password="pw")
    organizacao = OrganizacaoFactory(nome="Org Test")
    nucleo = NucleoFactory(organizacao=organizacao, nome="Nucleo Test")
    evento = EventoFactory(organizacao=organizacao, nucleo=nucleo, titulo="Evento Test")

    client = APIClient()
    client.force_login(user)
    sessionid = client.cookies.get("sessionid").value

    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        context = browser.new_context(base_url=live_server.url)
        context.add_cookies([{"name": "sessionid", "value": sessionid, "url": live_server.url}])
        page = context.new_page()
        page.goto(reverse("configuracoes-contextual-create"))

        page.select_option("#id_escopo_tipo", "organizacao")
        page.wait_for_selector(f"#id_escopo_id option[value='{organizacao.id}']")
        assert page.locator(f"#id_escopo_id option[value='{organizacao.id}']").inner_text() == organizacao.nome

        page.select_option("#id_escopo_tipo", "nucleo")
        page.wait_for_selector(f"#id_escopo_id option[value='{nucleo.id}']")
        assert page.locator(f"#id_escopo_id option[value='{nucleo.id}']").inner_text() == nucleo.nome

        page.select_option("#id_escopo_tipo", "evento")
        page.wait_for_selector(f"#id_escopo_id option[value='{evento.id}']")
        assert page.locator(f"#id_escopo_id option[value='{evento.id}']").inner_text() == evento.titulo

        browser.close()
