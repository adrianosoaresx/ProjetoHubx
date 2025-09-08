"""Template filters for string operations."""

from django import template

register = template.Library()


@register.filter(name="startswith")
def startswith(text: str, prefix: str) -> bool:
    """Return True if ``text`` starts with the given ``prefix``.

    Both arguments are converted to strings to avoid type errors when
    ``None`` or other non-string types are provided.
    """
    if text is None or prefix is None:
        return False
    return str(text).startswith(str(prefix))
