from __future__ import annotations

from decimal import Decimal

import pytest

from pagamentos.models import Pedido, Transacao
from pagamentos.providers import MercadoPagoProvider, PaymentProvider


def test_mercado_pago_provider_respects_interface() -> None:
    assert issubclass(MercadoPagoProvider, PaymentProvider)


@pytest.fixture
def mercado_pago_provider() -> MercadoPagoProvider:
    return MercadoPagoProvider(access_token="token", public_key="public")


@pytest.fixture
@pytest.mark.django_db
def pedido() -> Pedido:
    return Pedido.objects.create(valor=Decimal("100.00"))


@pytest.fixture
@pytest.mark.django_db
def transacao(pedido: Pedido) -> Transacao:
    return Transacao.objects.create(pedido=pedido, valor=pedido.valor)


@pytest.mark.django_db
def test_criar_cobranca_not_implemented(mercado_pago_provider: MercadoPagoProvider, pedido: Pedido) -> None:
    with pytest.raises(NotImplementedError):
        mercado_pago_provider.criar_cobranca(pedido)


@pytest.mark.django_db
def test_confirmar_pagamento_not_implemented(mercado_pago_provider: MercadoPagoProvider, transacao: Transacao) -> None:
    with pytest.raises(NotImplementedError):
        mercado_pago_provider.confirmar_pagamento(transacao)


@pytest.mark.django_db
def test_estornar_pagamento_not_implemented(mercado_pago_provider: MercadoPagoProvider, transacao: Transacao) -> None:
    with pytest.raises(NotImplementedError):
        mercado_pago_provider.estornar_pagamento(transacao)
