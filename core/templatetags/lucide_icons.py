from django import template
from django.utils.safestring import mark_safe
import lucide as lucide_lib

register = template.Library()


@register.simple_tag
def lucide(name: str, label: str | None = None, **attrs) -> str:
    """Render a Lucide SVG icon inline.

    Parameters
    ----------
    name: str
        Icon name as defined by lucide (e.g. "plus").
    label: Optional[str]
        Accessible label. If omitted the icon will be marked as decorative.
    **attrs: dict
        Additional HTML attributes to include in the rendered SVG
        (e.g. class, width, height).
    """
    if label:
        attrs["aria-label"] = label
    else:
        attrs["aria-hidden"] = "true"
    svg = lucide_lib._render_icon(name, None, **attrs)
    return mark_safe(svg)
