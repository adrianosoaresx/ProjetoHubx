import pytest
from django.core.cache import cache

from nucleos.tasks import limpar_contadores_convites

pytestmark = pytest.mark.django_db


def test_limpar_contadores_convites_without_delete_pattern(monkeypatch):
    cache.clear()
    cache.set("convites_nucleo:1", "a")
    cache.set("convites_nucleo:2", "b")
    cache.set("other", "c")

    # Simula backend sem suporte a delete_pattern
    monkeypatch.delattr(cache, "delete_pattern", raising=False)

    limpar_contadores_convites()

    assert cache.get("convites_nucleo:1") is None
    assert cache.get("convites_nucleo:2") is None
    assert cache.get("other") == "c"
