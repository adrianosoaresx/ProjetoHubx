"""Helpers related to navigation and history handling."""

from __future__ import annotations

from typing import Iterable
from urllib.parse import urlparse

from django.urls import NoReverseMatch, reverse
from django.utils.http import url_has_allowed_host_and_scheme


def _normalize_fallback(value: str | None) -> str | None:
    if not value:
        return None
    if value.startswith(("/", "http://", "https://")):
        return value
    try:
        return reverse(value)
    except NoReverseMatch:
        return value


BACK_NAVIGATION_FALLBACKS: dict[str, str] = {
    "feed:post_update": "feed:listar",
}


def get_back_navigation_fallback(request, *, fallback: str | None = None) -> str | None:
    match = getattr(request, "resolver_match", None)
    mapped = None
    if match is not None:
        mapped = BACK_NAVIGATION_FALLBACKS.get(match.view_name)
    return _normalize_fallback(mapped or fallback)


def resolve_back_href(
    request,
    *,
    fallback: str | None = None,
    disallow: Iterable[str] | None = None,
) -> str:
    """Return a safe URL to navigate back to.

    The function inspects HTMX headers and the HTTP referer, always falling
    back to ``fallback`` (or ``/`` when omitted) when none of the candidates is
    valid for the current host. The current path is ignored to avoid loops.
    """

    resolved_fallback = _normalize_fallback(fallback)

    allowed_hosts = {request.get_host()}
    current_path = request.get_full_path()
    disallow = set(disallow or []) | {current_path}

    candidates = [
        request.headers.get("HX-Current-URL"),
        request.META.get("HTTP_REFERER"),
        resolved_fallback,
    ]

    for candidate in candidates:
        if not candidate:
            continue
        if not url_has_allowed_host_and_scheme(
            candidate,
            allowed_hosts=allowed_hosts,
            require_https=request.is_secure(),
        ):
            continue

        parsed = urlparse(candidate)
        path = parsed.path or ""
        if parsed.query:
            path = f"{path}?{parsed.query}"
        if parsed.fragment:
            path = f"{path}#{parsed.fragment}"

        if path in disallow:
            continue

        return path or candidate

    if resolved_fallback and url_has_allowed_host_and_scheme(
        resolved_fallback,
        allowed_hosts=allowed_hosts,
        require_https=request.is_secure(),
    ):
        return resolved_fallback

    return "/"
