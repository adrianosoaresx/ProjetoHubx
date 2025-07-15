from django import template

def add_class(value, css_class):
    if hasattr(value, 'as_widget'):
        return value.as_widget(attrs={"class": css_class})
    return value

register = template.Library()
register.filter("add_class", add_class)
