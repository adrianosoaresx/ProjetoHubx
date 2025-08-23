from __future__ import annotations

from django.test.client import RequestFactory
from django.utils.cache import _generate_cache_key

# Cache key prefixes
CATEGORIAS_LIST_KEY_PREFIX = "discussao_categorias_list"
TOPICOS_LIST_KEY_PREFIX = "discussao_topicos_list"

_rf = RequestFactory()


def categorias_list_cache_key() -> str:
    """Return cache key for the categories listing view."""
    request = _rf.get("/discussao/")
    return _generate_cache_key(request, "GET", [], CATEGORIAS_LIST_KEY_PREFIX)


def topicos_list_cache_key(categoria_slug: str) -> str:
    """Return cache key for the topics listing view of a category."""
    request = _rf.get(f"/discussao/{categoria_slug}/")
    return _generate_cache_key(request, "GET", [], TOPICOS_LIST_KEY_PREFIX)
