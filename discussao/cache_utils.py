from __future__ import annotations

from typing import Mapping, Optional

from django.test.client import RequestFactory
from django.utils.cache import _generate_cache_key

# Cache key prefixes
CATEGORIAS_LIST_KEY_PREFIX = "discussao_categorias_list"
TOPICOS_LIST_KEY_PREFIX = "discussao_topicos_list"

_rf = RequestFactory()


def categorias_list_cache_key(
    *,
    user: Optional[object] = None,
    organizacao_id: Optional[int] = None,
    params: Optional[Mapping[str, object]] = None,
) -> str:
    """Return cache key for the categories listing view.

    The key incorporates the user or organization id when provided so caches
    are scoped per user/organization.
    """

    request = _rf.get("/discussao/", data=params or {})
    key = _generate_cache_key(request, "GET", [], CATEGORIAS_LIST_KEY_PREFIX)
    if user is not None:
        key = f"{key}:u{getattr(user, 'id', user)}"
    if organizacao_id is not None:
        key = f"{key}:o{organizacao_id}"
    return key


def topicos_list_cache_key(
    categoria_slug: str,
    *,
    user: Optional[object] = None,
    organizacao_id: Optional[int] = None,
    params: Optional[Mapping[str, object]] = None,
) -> str:
    """Return cache key for the topics listing view of a category.

    The key also varies according to the provided user or organization id.
    """

    request = _rf.get(f"/discussao/{categoria_slug}/", data=params or {})
    key = _generate_cache_key(request, "GET", [], TOPICOS_LIST_KEY_PREFIX)
    if user is not None:
        key = f"{key}:u{getattr(user, 'id', user)}"
    if organizacao_id is not None:
        key = f"{key}:o{organizacao_id}"
    return key
