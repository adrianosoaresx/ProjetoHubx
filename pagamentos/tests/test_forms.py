import os
from datetime import timedelta

import django
import pytest
from django.utils import timezone

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "Hubx.settings")
django.setup()

from pagamentos.forms import CheckoutForm  # noqa: E402
from pagamentos.models import Transacao  # noqa: E402


@pytest.fixture
def boleto_base_data() -> dict[str, str]:
    return {
        "valor": "100.00",
        "metodo": Transacao.Metodo.BOLETO,
        "email": "cliente@example.com",
        "nome": "Cliente Teste",
        "documento": "12345678909",
        "vencimento": (timezone.now() + timedelta(days=2)).isoformat(),
        "cep": "",
        "logradouro": "",
        "numero": "",
        "bairro": "",
        "cidade": "",
        "estado": "",
    }


def test_checkout_form_requires_address_fields_for_boleto(boleto_base_data: dict[str, str]) -> None:
    form = CheckoutForm(data=boleto_base_data)

    assert form.is_valid() is False
    for field in ["cep", "logradouro", "numero", "bairro", "cidade", "estado"]:
        assert field in form.errors


def test_checkout_form_validates_cep_and_estado(boleto_base_data: dict[str, str]) -> None:
    boleto_base_data.update(
        {
            "cep": "12345",
            "logradouro": "Rua A",
            "numero": "123",
            "bairro": "Centro",
            "cidade": "São Paulo",
            "estado": "sp",
        }
    )
    form = CheckoutForm(data=boleto_base_data)

    assert form.is_valid() is False
    assert "cep" in form.errors

    boleto_base_data["cep"] = "12345-678"
    form = CheckoutForm(data=boleto_base_data)

    assert form.is_valid() is True
    assert form.cleaned_data["cep"] == "12345678"
    assert form.cleaned_data["estado"] == "SP"
