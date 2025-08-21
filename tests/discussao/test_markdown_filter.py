from django.template import Context, Template


def render(template_string: str, context: dict | None = None) -> str:
    tpl = Template(template_string)
    return tpl.render(Context(context or {}))


def test_markdown_renders_basic_markdown():
    tpl = "{% load markdown_extras %}{{ text|markdown }}"
    rendered = render(tpl, {"text": "*oi*"})
    assert "<em>oi</em>" in rendered


def test_markdown_sanitizes_html():
    tpl = "{% load markdown_extras %}{{ text|markdown }}"
    rendered = render(tpl, {"text": "script <script>alert('x')</script>"})
    assert "<script>" not in rendered
    assert "alert('x')" in rendered
