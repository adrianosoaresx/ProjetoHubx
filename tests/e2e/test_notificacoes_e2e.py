import requests
import pytest
from django.urls import reverse
from rest_framework.test import APIClient
from playwright.sync_api import sync_playwright

from accounts.factories import UserFactory
from notificacoes.models import Canal, NotificationLog, NotificationTemplate
from notificacoes.tasks import enviar_relatorios_diarios

pytestmark = pytest.mark.django_db


def test_e2e_preferences_and_history(live_server, settings):
    settings.CELERY_TASK_ALWAYS_EAGER = True
    user = UserFactory(password="pw")
    client = APIClient()
    client.force_login(user)
    url = live_server.url + reverse("configuracoes_api:configuracoes-conta")
    resp = client.patch(url, {"tema": "escuro"}, format="json")
    assert resp.status_code == 200

    template = NotificationTemplate.objects.create(
        codigo="t1", assunto="a", corpo="msg", canal=Canal.EMAIL
    )
    NotificationLog.objects.create(user=user, template=template, canal=Canal.EMAIL)
    enviar_relatorios_diarios()

    sessionid = client.cookies.get("sessionid").value
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        context = browser.new_context(base_url=live_server.url)
        context.add_cookies(
            [{"name": "sessionid", "value": sessionid, "url": live_server.url}]
        )
        page = context.new_page()
        page.goto(reverse("notificacoes:historico"))
        try:
            axe_js = requests.get(
                "https://cdn.jsdelivr.net/npm/axe-core@4.7.2/axe.min.js", timeout=10
            ).text
            page.add_script_tag(content=axe_js)
            results = page.evaluate("async () => { return await axe.run(); }")
            assert results["violations"] == []
        except requests.RequestException:
            pytest.skip("axe-core indisponível")
        assert "msg" in page.content()
        browser.close()
