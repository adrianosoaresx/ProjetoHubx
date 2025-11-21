from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from pagamentos.models import Pedido, Transacao


class PaymentProvider(ABC):
    """Contrato base para provedores de pagamento."""

    @abstractmethod
    def criar_cobranca(self, pedido: Pedido) -> Any:
        """Cria uma cobrança para o pedido informado."""

    @abstractmethod
    def confirmar_pagamento(self, transacao: Transacao) -> Any:
        """Confirma o pagamento de uma transação previamente iniciada."""

    @abstractmethod
    def estornar_pagamento(self, transacao: Transacao) -> Any:
        """Realiza o estorno de uma transação aprovada."""
