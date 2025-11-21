from __future__ import annotations

from typing import Any

from pagamentos.models import Pedido, Transacao
from pagamentos.providers.base import PaymentProvider


class PagamentoService:
    """Serviço de domínio para orquestrar operações de pagamento."""

    def __init__(self, provider: PaymentProvider) -> None:
        self.provider = provider

    def criar_cobranca(self, pedido: Pedido) -> Any:
        """Delegar a criação de cobrança ao provedor configurado."""

        return self.provider.criar_cobranca(pedido)

    def confirmar_pagamento(self, transacao: Transacao) -> Any:
        """Delegar a confirmação de pagamento ao provedor."""

        return self.provider.confirmar_pagamento(transacao)

    def estornar_pagamento(self, transacao: Transacao) -> Any:
        """Delegar o estorno de pagamento ao provedor."""

        return self.provider.estornar_pagamento(transacao)
