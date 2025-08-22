import pytest
from bs4 import BeautifulSoup
from django.urls import reverse

pytestmark = pytest.mark.django_db


def test_notifications_preserves_htmx_attrs_after_swap(client, cliente_user):
    client.force_login(cliente_user)
    url = reverse("dashboard:notificacoes-partial")
    outer_html = (
        f'<section id="notifications" hx-get="{url}" '
        'hx-trigger="load, every 20s" hx-target="this" hx-swap="innerHTML"></section>'
    )
    soup = BeautifulSoup(outer_html, "html.parser")
    section = soup.find("section", id="notifications")
    attrs_before = dict(section.attrs)

    partial = client.get(url, HTTP_HX_REQUEST="true")
    assert partial.status_code == 200
    partial_soup = BeautifulSoup(partial.content, "html.parser")
    section.clear()
    section.append(partial_soup.find("section", id="notifications").decode_contents())

    assert dict(section.attrs) == attrs_before
