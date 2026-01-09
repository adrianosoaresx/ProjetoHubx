import os
from datetime import timedelta

import django
import pytest
from django.utils import timezone

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "Hubx.settings")
django.setup()

from pagamentos.forms import FaturamentoForm, PixCheckoutForm  # noqa: E402
from pagamentos.models import Transacao  # noqa: E402


def test_pix_checkout_form_expiracao_futura() -> None:
    form = PixCheckoutForm(
        data={
            "valor": "100.00",
            "metodo": Transacao.Metodo.PIX,
            "email": "cliente@example.com",
            "nome": "Cliente Teste",
            "documento": "12345678909",
            "pix_expiracao": (timezone.now() + timedelta(days=1)).isoformat(),
        }
    )

    assert form.is_valid() is True


def test_pix_checkout_form_expiracao_padrao(monkeypatch, settings) -> None:
    fixed_now = timezone.now()
    settings.PAGAMENTOS_PIX_EXPIRACAO_PADRAO_MINUTOS = 45
    monkeypatch.setattr("pagamentos.forms.timezone.now", lambda: fixed_now)
    form = PixCheckoutForm(
        data={
            "valor": "100.00",
            "metodo": Transacao.Metodo.PIX,
            "email": "cliente@example.com",
            "nome": "Cliente Teste",
            "documento": "12345678909",
        }
    )

    assert form.is_valid() is True
    assert form.cleaned_data["pix_expiracao"] == fixed_now + timedelta(minutes=45)


def test_pix_checkout_form_expiracao_invalida() -> None:
    form = PixCheckoutForm(
        data={
            "valor": "100.00",
            "metodo": Transacao.Metodo.PIX,
            "email": "cliente@example.com",
            "nome": "Cliente Teste",
            "documento": "12345678909",
            "pix_expiracao": (timezone.now() - timedelta(minutes=5)).isoformat(),
        }
    )

    assert form.is_valid() is False
    assert "pix_expiracao" in form.errors


def test_faturamento_form_requires_fields() -> None:
    form = FaturamentoForm(
        data={
            "valor": "250.00",
        }
    )

    assert form.is_valid() is False
    assert "inscricao_uuid" in form.errors
    assert "condicao_faturamento" in form.errors
