from __future__ import annotations

from decimal import Decimal
from types import SimpleNamespace
from typing import Any

import pytest
from django.http import HttpRequest

from pagamentos.exceptions import PagamentoInvalidoError
from pagamentos.models import Pedido, Transacao
from pagamentos.providers import MercadoPagoProvider, PaymentProvider
from pagamentos.services import PagamentoService
from pagamentos.views import WebhookView


def test_mercado_pago_provider_respects_interface() -> None:
    assert issubclass(MercadoPagoProvider, PaymentProvider)


@pytest.fixture
def mercado_pago_provider(monkeypatch: pytest.MonkeyPatch) -> MercadoPagoProvider:
    provider = MercadoPagoProvider(access_token="token", public_key="public")

    def fake_request(method: str, url: str, **kwargs: Any) -> SimpleNamespace:
        return SimpleNamespace(
            json=lambda: {"id": "123", "status": "approved"},
            raise_for_status=lambda: None,
        )

    monkeypatch.setattr(provider.session, "request", fake_request)
    return provider


@pytest.fixture
@pytest.mark.django_db
def pedido() -> Pedido:
    return Pedido.objects.create(valor=Decimal("100.00"))


@pytest.fixture
@pytest.mark.django_db
def transacao(pedido: Pedido) -> Transacao:
    return Transacao.objects.create(
        pedido=pedido,
        valor=pedido.valor,
        metodo=Transacao.Metodo.PIX,
        external_id="123",
    )


@pytest.mark.django_db
def test_criar_cobranca_pix(mercado_pago_provider: MercadoPagoProvider, pedido: Pedido) -> None:
    resposta = mercado_pago_provider.criar_cobranca(
        pedido, Transacao.Metodo.PIX, {"email": "a@b.com", "nome": "Pessoa", "document_number": "000"}
    )
    assert resposta["id"] == "123"


def test_metodo_invalido(pedido: Pedido, mercado_pago_provider: MercadoPagoProvider) -> None:
    with pytest.raises(PagamentoInvalidoError):
        mercado_pago_provider.criar_cobranca(pedido, "crypto", {"email": "a@b.com"})


@pytest.mark.django_db
def test_service_cria_transacao(pedido: Pedido, mercado_pago_provider: MercadoPagoProvider) -> None:
    service = PagamentoService(mercado_pago_provider)
    transacao = service.iniciar_pagamento(
        pedido,
        Transacao.Metodo.PIX,
        {"email": "user@example.com", "nome": "Nome", "document_number": "1"},
    )
    pedido.refresh_from_db()
    assert transacao.external_id == "123"
    assert pedido.status == Pedido.Status.PAGO


def test_estorno_sem_id(mercado_pago_provider: MercadoPagoProvider, pedido: Pedido) -> None:
    transacao_sem_id = Transacao(pedido=pedido, valor=pedido.valor, metodo=Transacao.Metodo.PIX)
    with pytest.raises(PagamentoInvalidoError):
        mercado_pago_provider.estornar_pagamento(transacao_sem_id)


def test_webhook_idempotente(monkeypatch: pytest.MonkeyPatch, transacao: Transacao) -> None:
    chamado = {"vezes": 0}

    class FakeProvider(MercadoPagoProvider):
        def __init__(self) -> None:  # pragma: no cover - simplificado para testes
            super().__init__(access_token="token")

        def confirmar_pagamento(self, transacao: Transacao) -> dict[str, Any]:  # type: ignore[override]
            chamado["vezes"] += 1
            return {"status": "approved"}

    view = WebhookView()
    view.provider_class = FakeProvider
    body = b"{\"data\": {\"id\": \"123\"}}"
    request = HttpRequest()
    request.method = "POST"
    request.body = body
    request.headers = {}

    response = view.post(request)
    assert response.status_code == 200
    assert chamado["vezes"] == 1
    # chamada repetida não altera status se já aprovado
    response = view.post(request)
    assert response.status_code == 200
    assert chamado["vezes"] == 2
