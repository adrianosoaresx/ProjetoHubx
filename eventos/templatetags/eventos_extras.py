from django import template

register = template.Library()

@register.filter
def dict_get(dict_obj, key):
    """Safely get a value from a dictionary in templates."""
    return dict_obj.get(key)
