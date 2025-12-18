import os
import types
from typing import Any

import django
import pytest
from django.conf import settings

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "Hubx.settings")
django.setup()

from pagamentos.providers.base import PaymentProvider  # noqa: E402
from pagamentos.services import pagamento  # noqa: E402
from pagamentos.services.pagamento import PagamentoService  # noqa: E402


def _make_service() -> PagamentoService:
    class DummyProvider(PaymentProvider):
        def criar_cobranca(self, pedido: Any, metodo: str, dados_pagamento: dict[str, Any] | None = None) -> Any:
            raise NotImplementedError

        def confirmar_pagamento(self, transacao: Any) -> Any:
            raise NotImplementedError

        def estornar_pagamento(self, transacao: Any) -> Any:
            raise NotImplementedError

        def consultar_pagamento(self, transacao: Any) -> Any:
            raise NotImplementedError

    return PagamentoService(DummyProvider())


@pytest.mark.django_db
def test_row_locking_enabled_uses_has_select_for_update(monkeypatch: pytest.MonkeyPatch) -> None:
    service = _make_service()

    features = types.SimpleNamespace(has_select_for_update=True, supports_select_for_update=False)
    monkeypatch.setattr(
        pagamento,
        "connections",
        {"default": types.SimpleNamespace(features=features)},
        raising=False,
    )
    settings.PAGAMENTOS_ROW_LOCKS_ENABLED = True

    assert service._row_locking_enabled("default") is True


@pytest.mark.django_db
def test_row_locking_enabled_falls_back_to_supports(monkeypatch: pytest.MonkeyPatch) -> None:
    service = _make_service()

    features = types.SimpleNamespace(supports_select_for_update=True)
    monkeypatch.setattr(
        pagamento,
        "connections",
        {"default": types.SimpleNamespace(features=features)},
        raising=False,
    )
    settings.PAGAMENTOS_ROW_LOCKS_ENABLED = True

    assert service._row_locking_enabled("default") is True


@pytest.mark.django_db
def test_row_locking_enabled_returns_bool_with_missing_features(monkeypatch: pytest.MonkeyPatch) -> None:
    service = _make_service()

    features = types.SimpleNamespace()
    monkeypatch.setattr(
        pagamento,
        "connections",
        {"default": types.SimpleNamespace(features=features)},
        raising=False,
    )
    settings.PAGAMENTOS_ROW_LOCKS_ENABLED = True

    assert service._row_locking_enabled("default") is False
