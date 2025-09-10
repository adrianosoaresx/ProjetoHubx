"""Custom template filters for empresas app."""

from django import template
from django.forms.boundfield import BoundField


register = template.Library()


@register.filter(name="add_class")
def add_class(value: BoundField, css_class: str) -> BoundField:
    """Add a CSS class to a form field and return the original ``BoundField``.

    This modifies the widget's ``class`` attribute in place and returns the
    unrendered ``BoundField`` so that additional filters (e.g. ``attr`` from
    ``widget_tweaks``) can be chained afterwards.
    """

    existing = value.field.widget.attrs.get("class", "")
    value.field.widget.attrs["class"] = f"{existing} {css_class}".strip()
    return value
