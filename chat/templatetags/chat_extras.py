from django import template
from django.conf import settings

register = template.Library()

@register.filter
def absolute_media(path, request=None):
    """Return absolute URL for media files."""
    if not path:
        return ""
    if path.startswith("http://") or path.startswith("https://"):
        return path

    url = settings.MEDIA_URL.rstrip("/") + "/" + path.lstrip("/")
    if request is None:
        return url
    return request.build_absolute_uri(url)
