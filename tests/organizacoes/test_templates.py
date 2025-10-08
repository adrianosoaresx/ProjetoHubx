from types import SimpleNamespace

from django.template.loader import render_to_string


def test_hero_organizacao_renders_stats_block():
    context = {
        "organizacao": SimpleNamespace(nome="Org de Teste"),
        "title": "Org de Teste",
        "subtitle": "Subtítulo",
        "neural_background": "home",
        "show_stats": True,
        "usuarios_total": 7,
        "nucleos_total": 3,
        "eventos_total": 2,
    }

    html = render_to_string("_components/hero_organizacao.html", context)

    assert "Org de Teste" in html
    assert "7" in html
    assert "3" in html
    assert "2" in html
