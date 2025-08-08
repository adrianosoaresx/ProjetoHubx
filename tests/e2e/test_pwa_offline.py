import pytest
from django.urls import reverse
from playwright.sync_api import sync_playwright
from rest_framework.test import APIClient

from accounts.factories import UserFactory

pytestmark = pytest.mark.django_db


def test_dashboard_pwa_offline(live_server):
    user = UserFactory(password="pw")
    client = APIClient()
    client.force_login(user)
    sessionid = client.cookies.get("sessionid").value

    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        context = browser.new_context(base_url=live_server.url)
        context.add_cookies([{"name": "sessionid", "value": sessionid, "url": live_server.url}])
        page = context.new_page()
        page.goto(reverse("dashboard:dashboard"))

        # Ensure service worker is controlling the page
        page.wait_for_function("navigator.serviceWorker.controller !== null")
        manifest = page.get_attribute("link[rel='manifest']", "href")
        assert manifest and manifest.endswith("manifest.json")

        metrics = page.evaluate("fetch('/dashboard/metrics-partial/').then(r => r.text())")
        context.set_offline(True)
        offline_metrics = page.evaluate("fetch('/dashboard/metrics-partial/').then(r => r.text())")
        assert offline_metrics == metrics

        browser.close()
