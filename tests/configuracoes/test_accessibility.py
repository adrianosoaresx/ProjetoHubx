import pytest
from django.urls import reverse

axe_module = pytest.importorskip("axe_core_python.sync_playwright")
playwright_module = pytest.importorskip("playwright.sync_api")

Axe = axe_module.Axe
sync_playwright = playwright_module.sync_playwright

pytestmark = pytest.mark.django_db


def test_configuracoes_sem_violacoes(client, admin_user):
    client.force_login(admin_user)
    response = client.get(reverse("configuracoes:configuracoes"))
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
