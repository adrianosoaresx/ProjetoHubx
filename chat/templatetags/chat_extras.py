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
    if request is None:
        # Without request we just prepend MEDIA_URL
        return settings.MEDIA_URL.rstrip('/') + '/' + path.lstrip('/')
    return request.build_absolute_uri(path)
