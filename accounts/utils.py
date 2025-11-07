from __future__ import annotations

from typing import Iterable

from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect
from django.urls import reverse


def is_htmx_or_ajax(request: HttpRequest) -> bool:
    """Return whether the request was triggered via HTMX or XMLHttpRequest."""

    if request.headers.get("HX-Request"):
        return True
    requested_with = request.headers.get("X-Requested-With", "")
    return isinstance(requested_with, str) and requested_with.lower() == "xmlhttprequest"


def build_profile_section_url(
    request: HttpRequest,
    section: str,
    extra_params: dict[str, str | None] | None = None,
    *,
    allowed_sections: Iterable[str] | None = None,
) -> str:
    params = request.GET.copy()
    params = params.copy()
    if extra_params:
        for key, value in extra_params.items():
            if value is None:
                params.pop(key, None)
            else:
                params[key] = value
    params["section"] = section
    if allowed_sections is not None and section not in allowed_sections:
        params["section"] = next(iter(allowed_sections), section)
    query_string = params.urlencode()
    url = reverse("accounts:perfil")
    if query_string:
        url = f"{url}?{query_string}"
    return url


def redirect_to_profile_section(
    request: HttpRequest,
    section: str,
    extra_params: dict[str, str | None] | None = None,
    *,
    allowed_sections: Iterable[str] | None = None,
):
    url = build_profile_section_url(
        request,
        section,
        extra_params,
        allowed_sections=allowed_sections,
    )
    if request.headers.get("HX-Request"):
        response = HttpResponse(status=204)
        response["HX-Redirect"] = url
        return response
    return redirect(url)


__all__ = ["build_profile_section_url", "is_htmx_or_ajax", "redirect_to_profile_section"]
