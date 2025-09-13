"""Template filters for common string and mapping operations."""

from django import template

register = template.Library()


@register.filter(name="startswith")
def startswith(text: str, prefix: str) -> bool:
    """Return ``True`` if ``text`` starts with the given ``prefix``.

    Both arguments are converted to strings to avoid type errors when
    ``None`` or other non-string types are provided.
    """
    if text is None or prefix is None:
        return False
    return str(text).startswith(str(prefix))


@register.filter(name="split")
def split(value: str | None, delimiter: str = " "):
    """Split ``value`` by ``delimiter`` and return a list.

    If ``value`` is ``None`` an empty list is returned. The value is
    converted to ``str`` before splitting to avoid type issues.
    """
    if value is None:
        return []
    return str(value).split(delimiter)


@register.filter(name="get_item")
def get_item(mapping, key):
    """Return ``mapping[key]`` for dictionaries or attributes.

    When ``mapping`` is ``None`` or the key does not exist ``None`` is
    returned. This allows safe lookups in templates without raising
    exceptions.
    """
    if mapping is None:
        return None
    if isinstance(mapping, dict):
        return mapping.get(key)
    return getattr(mapping, key, None)
