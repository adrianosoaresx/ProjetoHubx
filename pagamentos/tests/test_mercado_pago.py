from datetime import datetime, timedelta, timezone as dt_timezone
import sys
import types

import django
import pytest
from django.conf import settings
from django.utils import timezone

if not settings.configured:
    settings.configure(
        USE_TZ=True,
        TIME_ZONE="America/Sao_Paulo",
        INSTALLED_APPS=[],
        SECRET_KEY="testing",
    )

django.setup()

pagamentos_models = types.ModuleType("pagamentos.models")


class DummyTransacao:
    class Metodo:
        PIX = "pix"
        CARTAO = "cartao"
        BOLETO = "boleto"


class DummyPedido:
    def __init__(self, valor: float) -> None:
        self.valor = valor


pagamentos_models.Pedido = DummyPedido
pagamentos_models.Transacao = DummyTransacao
sys.modules.setdefault("pagamentos.models", pagamentos_models)

pagamentos_base = types.ModuleType("pagamentos.providers.base")


class PaymentProvider:  # pragma: no cover - stub only
    pass


pagamentos_base.PaymentProvider = PaymentProvider
sys.modules.setdefault("pagamentos.providers.base", pagamentos_base)

pagamentos_paypal = types.ModuleType("pagamentos.providers.paypal")


class PayPalProvider:  # pragma: no cover - stub only
    pass


pagamentos_paypal.PayPalProvider = PayPalProvider
sys.modules.setdefault("pagamentos.providers.paypal", pagamentos_paypal)

from pagamentos.exceptions import PagamentoInvalidoError  # noqa: E402
from pagamentos.providers.mercado_pago import MercadoPagoProvider  # noqa: E402


@pytest.fixture
def provider() -> MercadoPagoProvider:
    return MercadoPagoProvider(access_token="test", public_key="test", base_url="https://example.com")


def test_payer_data_with_full_name(provider: MercadoPagoProvider) -> None:
    dados_pagamento = {
        "nome": "João Silva",
        "email": "joao@example.com",
        "document_number": "12345678901",
    }

    payer = provider._payer_data(dados_pagamento)

    assert payer["first_name"] == "João"
    assert payer["last_name"] == "Silva"


def test_payer_data_with_single_name(provider: MercadoPagoProvider) -> None:
    dados_pagamento = {
        "nome": "Maria",
        "email": "maria@example.com",
        "document_number": "10987654321",
    }

    payer = provider._payer_data(dados_pagamento)

    assert payer["first_name"] == "Maria"
    assert payer["last_name"] == "Maria"


def test_payer_data_includes_address(provider: MercadoPagoProvider) -> None:
    dados_pagamento = {
        "nome": "Carlos Alberto",
        "email": "carlos@example.com",
        "document_number": "98765432100",
        "zip_code": "12345678",
        "street_name": "Rua das Flores",
        "street_number": "123",
        "neighborhood": "Centro",
        "city": "São Paulo",
        "federal_unit": "SP",
    }

    payer = provider._payer_data(dados_pagamento)

    assert payer["address"] == {
        "zip_code": "12345678",
        "street_name": "Rua das Flores",
        "street_number": "123",
        "neighborhood": "Centro",
        "city": "São Paulo",
        "federal_unit": "SP",
    }


def test_format_datetime_from_datetime(provider: MercadoPagoProvider) -> None:
    dt_value = datetime(2025, 12, 17, 21, 50, 13, tzinfo=dt_timezone.utc)

    formatted = provider._format_datetime(dt_value)

    assert formatted == "2025-12-17T18:50:13.000-03:00"


def test_format_datetime_from_iso_string_with_offset(provider: MercadoPagoProvider) -> None:
    formatted = provider._format_datetime("2025-12-17T21:50:13-03:00")

    assert formatted == "2025-12-17T21:50:13.000-03:00"


def test_format_datetime_from_br_format_with_timezone(provider: MercadoPagoProvider) -> None:
    formatted = provider._format_datetime("17/12/2025 21:50:13 -03:00")

    assert formatted == "2025-12-17T21:50:13.000-03:00"


def test_format_datetime_from_dash_format_with_metadata(provider: MercadoPagoProvider) -> None:
    formatted = provider._format_datetime("18-12-2025T13:14:54UTC;2a602e83-fe52-457e-86cb-d606530f6443")

    assert formatted == "2025-12-18T10:14:54.000-03:00"


def test_format_datetime_from_date(provider: MercadoPagoProvider) -> None:
    formatted = provider._format_datetime(datetime(2025, 12, 18).date())

    assert formatted == "2025-12-18T20:59:59.000-03:00"


def test_format_datetime_rejects_invalid_string(provider: MercadoPagoProvider) -> None:
    with pytest.raises(PagamentoInvalidoError):
        provider._format_datetime("17-12-2025 21:50")


def test_build_boleto_payload_normalizes_expiration(provider: MercadoPagoProvider) -> None:
    future_due = timezone.now() + timedelta(days=2)
    pedido = DummyPedido(100)
    dados_pagamento = {"vencimento": future_due, "email": "cliente@example.com"}

    payload = provider._build_boleto_payload(pedido, dados_pagamento)

    assert payload["date_of_expiration"] == provider._format_datetime(future_due)


def test_build_boleto_payload_rejects_invalid_expiration(provider: MercadoPagoProvider) -> None:
    pedido = DummyPedido(50)
    dados_pagamento = {"vencimento": "17-12-2099", "email": "cliente@example.com"}

    payload = provider._build_boleto_payload(pedido, dados_pagamento)

    assert payload["date_of_expiration"] == "2099-12-17T20:59:59.000-03:00"


def test_build_boleto_payload_rejects_dash_only_date(provider: MercadoPagoProvider) -> None:
    pedido = DummyPedido(50)
    dados_pagamento = {"vencimento": "17/12/2099", "email": "cliente@example.com"}

    payload = provider._build_boleto_payload(pedido, dados_pagamento)

    assert payload["date_of_expiration"] == "2099-12-17T20:59:59.000-03:00"


def test_build_boleto_payload_accepts_date_object(provider: MercadoPagoProvider) -> None:
    pedido = DummyPedido(50)
    vencimento = datetime(2099, 12, 17).date()
    dados_pagamento = {"vencimento": vencimento, "email": "cliente@example.com"}

    payload = provider._build_boleto_payload(pedido, dados_pagamento)

    assert payload["date_of_expiration"] == "2099-12-17T20:59:59.000-03:00"


def test_build_boleto_payload_strips_metadata(provider: MercadoPagoProvider) -> None:
    pedido = DummyPedido(75)
    vencimento = "2099-12-17T21:50:13UTC;idempotencia"
    dados_pagamento = {"vencimento": vencimento, "email": "cliente@example.com"}

    payload = provider._build_boleto_payload(pedido, dados_pagamento)

    assert payload["date_of_expiration"] == "2099-12-17T18:50:13.000-03:00"


def test_build_boleto_payload_accepts_timezone_aware_datetime(
    provider: MercadoPagoProvider,
) -> None:
    pedido = DummyPedido(75)
    vencimento = datetime(2099, 12, 17, 21, 50, 13, tzinfo=dt_timezone(timedelta(hours=-3)))
    dados_pagamento = {"vencimento": vencimento, "email": "cliente@example.com"}

    payload = provider._build_boleto_payload(pedido, dados_pagamento)

    assert payload["date_of_expiration"] == "2099-12-17T21:50:13.000-03:00"


def test_build_cartao_payload_respects_payment_method(provider: MercadoPagoProvider) -> None:
    pedido = DummyPedido(120)
    dados_pagamento = {
        "token": "master-token",
        "payment_method_id": "master",
        "email": "cliente@example.com",
    }

    payload = provider._build_cartao_payload(pedido, dados_pagamento)

    assert payload["payment_method_id"] == "master"


def test_build_cartao_payload_accepts_different_brands(provider: MercadoPagoProvider) -> None:
    pedido = DummyPedido(80)
    dados_pagamento = {
        "token": "amex-token",
        "payment_method_id": "amex",
        "email": "cliente@example.com",
    }

    payload = provider._build_cartao_payload(pedido, dados_pagamento)

    assert payload["payment_method_id"] == "amex"


def test_build_cartao_payload_requires_payment_method(provider: MercadoPagoProvider) -> None:
    pedido = DummyPedido(75)
    dados_pagamento = {
        "token": "missing-brand-token",
        "email": "cliente@example.com",
    }

    with pytest.raises(PagamentoInvalidoError) as excinfo:
        provider._build_cartao_payload(pedido, dados_pagamento)

    assert "Bandeira" in str(excinfo.value)
