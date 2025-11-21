from __future__ import annotations

import os
from typing import Any

from pagamentos.models import Pedido, Transacao
from pagamentos.providers.base import PaymentProvider


class MercadoPagoProvider(PaymentProvider):
    """Implementação de exemplo do provedor Mercado Pago."""

    def __init__(self, access_token: str | None = None, public_key: str | None = None) -> None:
        self.access_token = access_token or os.getenv("MERCADO_PAGO_ACCESS_TOKEN", "")
        self.public_key = public_key or os.getenv("MERCADO_PAGO_PUBLIC_KEY", "")

    def criar_cobranca(self, pedido: Pedido) -> Any:
        """
        Cria uma preferência de pagamento para o pedido.

        A chamada real à API do Mercado Pago será implementada na próxima fase.
        """

        raise NotImplementedError("Integração Mercado Pago pendente")

    def confirmar_pagamento(self, transacao: Transacao) -> Any:
        """
        Confirma o pagamento associado a uma transação.

        A confirmação depende do callback ou da consulta ativa ao status no provedor.
        """

        raise NotImplementedError("Integração Mercado Pago pendente")

    def estornar_pagamento(self, transacao: Transacao) -> Any:
        """
        Solicita o estorno de uma transação já capturada.

        O método deve ser implementado com as APIs oficiais do Mercado Pago.
        """

        raise NotImplementedError("Integração Mercado Pago pendente")
