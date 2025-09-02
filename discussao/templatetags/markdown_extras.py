from __future__ import annotations

import markdown as md
import bleach
from django import template
from django.utils.safestring import mark_safe

ALLOWED_TAGS = [
    "p",
    "pre",
    "span",
    "h1",
    "h2",
    "h3",
    "h4",
    "h5",
    "h6",
    "ul",
    "ol",
    "li",
    "blockquote",
    "code",
    "em",
    "strong",
    "a",
    "img",
    "hr",
    "br",
]
ALLOWED_ATTRIBUTES = {
    "a": ["href", "title", "rel"],
    "img": ["src", "alt", "title"],
}

register = template.Library()


@register.filter(name="markdown")
def markdown_filter(text: str | None) -> str:
    if not text:
        return ""
    html = md.markdown(text)
    cleaned = bleach.clean(
        html, tags=ALLOWED_TAGS, attributes=ALLOWED_ATTRIBUTES, strip=True
    )
    return mark_safe(cleaned)
