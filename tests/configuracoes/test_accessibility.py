import pytest
from axe_core_python.sync_playwright import Axe
from django.urls import reverse
from playwright.sync_api import sync_playwright

pytestmark = pytest.mark.django_db


@pytest.mark.xfail(reason="Acessibilidade ainda em melhoria", strict=True)
def test_configuracoes_sem_violacoes(client, admin_user):
    client.force_login(admin_user)
    response = client.get(reverse("configuracoes"))
    html = response.content.decode("utf-8")

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.set_content(html)
        axe = Axe()
        results = axe.run(page)
        browser.close()
    violations = [v for v in results["violations"] if v["id"] not in {"aria-required-children"}]
    assert violations == []
