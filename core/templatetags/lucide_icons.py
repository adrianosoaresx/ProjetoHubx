from django import template
from django.utils.safestring import mark_safe
import logging

logger = logging.getLogger(__name__)

try:  # Tornar dependência graciosa: se não instalado, não derruba o servidor.
    import lucide as lucide_lib  # type: ignore
except Exception as exc:  # ImportError ou outros problemas ao importar
    lucide_lib = None  # type: ignore
    logger.warning("Pacote 'lucide' não disponível. Ícones inline serão omitidos. Erro: %s", exc)

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
    if lucide_lib is None:
        # Fallback seguro: evita quebrar template; inclui comentário para depuração.
        return mark_safe(f"<!-- lucide não instalado: {name} -->")

    if label:
        attrs["aria-label"] = label
    else:
        attrs["aria-hidden"] = "true"
    try:
        svg = lucide_lib._render_icon(name, None, **attrs)  # type: ignore[attr-defined]
    except Exception as exc:
        logger.error("Falha ao renderizar ícone lucide '%s': %s", name, exc)
        return mark_safe(f"<!-- erro lucide: {name} -->")
    return mark_safe(svg)
