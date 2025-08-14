import pytest
from django.template.loader import render_to_string
from django.test import RequestFactory
from django.utils import translation, timezone
from types import SimpleNamespace
from bs4 import BeautifulSoup


@pytest.mark.parametrize("lang, direction", [("en", "ltr"), ("pt-br", "ltr")])
def test_base_template_has_lang_and_dir(lang, direction):
    rf = RequestFactory()
    request = rf.get("/")
    with translation.override(lang):
        html = render_to_string("base.html", {"request": request})
    soup = BeautifulSoup(html, "html.parser")
    assert soup.html.get("lang") == lang
    assert soup.html.get("dir") == direction


@pytest.mark.parametrize("template", [
    "dashboard/cliente.html",
    "dashboard/gerente.html",
])
def test_dashboard_templates_aria_label_translated(template):
    rf = RequestFactory()
    request = rf.get("/")
    with translation.override("en"):
        html = render_to_string(template, {"request": request})
    soup = BeautifulSoup(html, "html.parser")
    main = soup.select_one("main[aria-label]")
    assert main is not None
    assert main.get("aria-label") == "Dashboard"


def test_chat_file_attachment_has_translated_aria_label():
    rf = RequestFactory()
    request = rf.get("/")
    file = SimpleNamespace(name="report.pdf", url="/media/report.pdf")
    user = SimpleNamespace(username="john", profile=SimpleNamespace(avatar=None))
    message = SimpleNamespace(
        id=1,
        tipo="file",
        arquivo=file,
        remetente=user,
        created=timezone.now(),
        pinned_at=None,
        hidden_at=None,
        reaction_counts={},
    )
    with translation.override("en"):
        html = render_to_string(
            "chat/partials/message.html",
            {"m": message, "is_admin": False, "request": request},
        )
    soup = BeautifulSoup(html, "html.parser")
    link = soup.find("a", {"href": "/media/report.pdf"})
    assert link.get("aria-label") == "Download file"
