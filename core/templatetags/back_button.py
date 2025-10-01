from __future__ import annotations

from django import template
from django.utils.translation import gettext as _

register = template.Library()


HTMX_ATTRS: tuple[str, ...] = (
    "hx_get",
    "hx_post",
    "hx_put",
    "hx_delete",
    "hx_patch",
    "hx_target",
    "hx_swap",
    "hx_trigger",
    "hx_push_url",
    "hx_include",
    "hx_indicator",
    "hx_confirm",
    "hx_params",
    "hx_ext",
    "hx_on",
    "hx_vals",
    "hx_select",
    "hx_select_oob",
    "hx_replace_url",
    "hx_headers",
    "hx_prompt",
    "hx_validate",
    "hx_sync",
    "hx_boost",
    "hx_disable",
    "hx_history",
)


@register.simple_tag(takes_context=True)
def prepare_back_button(context: template.Context) -> dict:
    ctx = context.flatten()
    config = ctx.get("config")
    back_config = ctx.get("back_component_config")

    base_config: dict = {}
    if isinstance(config, dict):
        base_config.update(config)
    if not base_config and isinstance(back_config, dict):
        base_config.update(back_config)

    result: dict[str, object | None] = {}
    keys = (
        "href",
        "fallback_href",
        "variant",
        "classes",
        "label",
        "aria_label",
        "icon",
        "show_icon",
        "prevent_history",
    ) + HTMX_ATTRS

    for key in keys:
        if key in ctx:
            result[key] = ctx[key]
        elif key in base_config:
            result[key] = base_config.get(key)
        else:
            result[key] = None

    button_label = result.get("label") or _("Voltar")
    aria_label = result.get("aria_label") or button_label
    variant = (result.get("variant") or "button").strip()
    classes = (result.get("classes") or "").strip()
    icon_name = (result.get("icon") or "arrow-left").strip()

    show_icon = result.get("show_icon")
    if show_icon is None:
        show_icon = True

    def _boolean_attr(value):
        if isinstance(value, str):
            return value.lower()
        if isinstance(value, bool):
            return "true" if value else "false"
        return value

    htmx_attrs: list[tuple[str, str]] = []
    for attr in HTMX_ATTRS:
        value = result.get(attr)
        if value in (None, ""):
            continue
        if attr in {"hx_push_url", "hx_replace_url", "hx_boost", "hx_history"}:
            value = _boolean_attr(value)
        htmx_attrs.append((attr.replace("_", "-"), str(value)))

    prevent_history = result.get("prevent_history")
    if prevent_history in ("", None):
        prevent_history_attr = None
    else:
        prevent_history_attr = "true" if str(prevent_history).lower() == "true" else "false"

    if variant == "link":
        base_class = (
            "inline-flex items-center gap-1 text-sm font-medium text-primary-600 "
            "transition-colors hover:text-primary-700 focus-visible:outline "
            "focus-visible:outline-2 focus-visible:outline-offset-2 "
            "focus-visible:outline-primary-500"
        )
        label_class = "text-sm"
        icon_size = "w-4 h-4"
    elif variant == "compact":
        base_class = (
            "inline-flex items-center gap-1 text-xs font-medium text-primary-600 "
            "transition-colors hover:text-primary-700 focus-visible:outline "
            "focus-visible:outline-2 focus-visible:outline-offset-2 "
            "focus-visible:outline-primary-500"
        )
        label_class = "text-xs"
        icon_size = "w-3.5 h-3.5"
    else:
        base_class = "btn btn-secondary inline-flex items-center gap-2"
        label_class = "text-sm font-medium"
        icon_size = "w-4 h-4"

    if classes:
        base_class = f"{base_class} {classes}"

    href = result.get("href") or result.get("fallback_href") or "#"

    return {
        "href": href,
        "fallback_href": result.get("fallback_href"),
        "class_attr": base_class,
        "label": button_label,
        "aria_label": aria_label,
        "icon_name": icon_name,
        "icon_size": icon_size,
        "show_icon": show_icon is not False,
        "label_class": label_class,
        "prevent_history": prevent_history_attr,
        "htmx_attrs": htmx_attrs,
    }
