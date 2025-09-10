import re
from pathlib import Path
from types import SimpleNamespace

import pytest
from bs4 import BeautifulSoup
from django.contrib.auth.models import AnonymousUser
from django.template.loader import render_to_string
from django.test import RequestFactory
from django.urls import reverse
from django.utils import translation

ROOT = Path(__file__).resolve().parent.parent


def _template_name(path: Path) -> str:
    parts = path.parts
    idx = parts.index("templates")
    return "/".join(parts[idx + 1 :])


ALL_TEMPLATES = []
FULL_TEMPLATES = []
GETTEXT_TEMPLATES = []
for path in ROOT.rglob("templates/**/*.html"):
    text = path.read_text(encoding="utf-8")
    name = _template_name(path)
    ALL_TEMPLATES.append((name, path))
    if "<html" in text:
        FULL_TEMPLATES.append((name, path))
    if re.search(r"<script[^>]*>.*gettext\(", text, re.DOTALL):
        GETTEXT_TEMPLATES.append((name, path))


PT_CHARS = re.compile(r"[áàâãéèêíïóôõöúüçÁÀÂÃÉÈÊÍÏÓÔÕÖÚÜÇ]")
I18N_TAG = re.compile(r"{%(?:\s*)(trans|blocktrans|translate)\b|_\(|gettext\(")


@pytest.mark.parametrize("template_name,path", ALL_TEMPLATES)
def test_no_untranslated_pt_strings(template_name: str, path: Path):
    text = path.read_text(encoding="utf-8")
    text = re.sub(r"<!--.*?-->", "", text, flags=re.DOTALL)
    text = re.sub(r"{%-?\s*comment\s*-?%}.*?{%-?\s*endcomment\s*-?%}", "", text, flags=re.DOTALL)
    text = re.sub(r"<script.*?</script>", "", text, flags=re.DOTALL)
    for lineno, line in enumerate(text.splitlines(), 1):
        if PT_CHARS.search(line) and not I18N_TAG.search(line):
            pytest.fail(f"Untranslated PT string in {template_name}:{lineno}: {line.strip()}")


def _build_request(template_name: str):
    rf = RequestFactory()
    request = rf.get("/")
    if template_name.startswith("accounts/"):
        request.user = SimpleNamespace(
            is_authenticated=True,
            avatar=None,
            username="john",
            get_full_name=lambda: "John Doe",
            two_factor_enabled=False,
        )
    else:
        request.user = AnonymousUser()
    return request


def _context(template_name: str):
    request = _build_request(template_name)
    ctx = {"request": request}
    if template_name == "dashboard/export_pdf.html":
        ctx["metrics"] = {}
    if template_name == "financeiro/relatorios.html":
        ctx.update({"centros": [], "nucleos": []})
    return ctx


@pytest.mark.parametrize("template_name,_path", FULL_TEMPLATES)
@pytest.mark.parametrize("lang, direction", [("en", "ltr"), ("pt-br", "ltr")])
def test_templates_lang_and_dir(template_name: str, _path: Path, lang: str, direction: str):
    ctx = _context(template_name)
    with translation.override(lang):
        html = render_to_string(template_name, ctx)
    soup = BeautifulSoup(html, "html.parser")
    assert soup.html.get("lang") == lang
    assert soup.html.get("dir") == direction


@pytest.mark.parametrize("template_name,_path", GETTEXT_TEMPLATES)
def test_js_catalog_included(template_name: str, _path: Path):
    ctx = _context(template_name)
    html = render_to_string(template_name, ctx)
    js_catalog_url = reverse("javascript-catalog")
    soup = BeautifulSoup(html, "html.parser")
    assert soup.find("script", src=js_catalog_url) is not None
