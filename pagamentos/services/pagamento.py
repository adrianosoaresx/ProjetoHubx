from __future__ import annotations

from typing import Any, Iterable

from django.db import transaction

from pagamentos.exceptions import PagamentoInvalidoError
from pagamentos.models import Pedido, Transacao
from pagamentos.providers.base import PaymentProvider


class PagamentoService:
    """Serviço de domínio para orquestrar operações de pagamento."""

    def __init__(self, provider: PaymentProvider) -> None:
        self.provider = provider

    def iniciar_pagamento(
        self, pedido: Pedido, metodo: str, dados_pagamento: dict[str, Any] | None = None
    ) -> Transacao:
        """Cria a cobrança no provedor e registra a transação localmente."""

        if metodo not in Transacao.Metodo.values:
            raise PagamentoInvalidoError("Método inválido")

        resposta = self.provider.criar_cobranca(pedido, metodo, dados_pagamento)
        status = self._mapear_status(resposta.get("status"))
        external_id = str(resposta.get("id")) if resposta.get("id") else None

        with transaction.atomic():
            transacao = Transacao.objects.create(
                pedido=pedido,
                valor=pedido.valor,
                status=status,
                metodo=metodo,
                external_id=external_id,
            )
            self._sincronizar_pedido(pedido, status, external_id)
        return transacao

    def confirmar_pagamento(self, transacao: Transacao) -> Transacao:
        """Consulta o provedor e sincroniza o status local."""

        resposta = self.provider.confirmar_pagamento(transacao)
        status = self._mapear_status(resposta.get("status"))
        with transaction.atomic():
            self._atualizar_transacao(transacao, status)
            self._sincronizar_pedido(transacao.pedido, status, resposta.get("order_id"))
        return transacao

    def estornar_pagamento(self, transacao: Transacao) -> Transacao:
        """Delegar o estorno de pagamento ao provedor."""

        resposta = self.provider.estornar_pagamento(transacao)
        status = self._mapear_status(resposta.get("status") or Transacao.Status.ESTORNADA)
        with transaction.atomic():
            self._atualizar_transacao(transacao, status)
            self._sincronizar_pedido(transacao.pedido, status, resposta.get("order_id"))
        return transacao

    def _sincronizar_pedido(
        self, pedido: Pedido, status_transacao: str, external_id: str | None
    ) -> None:
        atualizacoes: dict[str, Any] = {}
        if external_id and pedido.external_id != external_id:
            pedido.external_id = external_id
            atualizacoes["external_id"] = external_id

        if status_transacao == Transacao.Status.APROVADA:
            novo_status = Pedido.Status.PAGO
        elif status_transacao == Transacao.Status.ESTORNADA:
            novo_status = Pedido.Status.CANCELADO
        else:
            novo_status = Pedido.Status.PENDENTE

        if pedido.status != novo_status:
            pedido.status = novo_status
            atualizacoes["status"] = novo_status

        if atualizacoes:
            pedido.save(update_fields=self._campos_atualizacao(atualizacoes.keys()))

    def _atualizar_transacao(self, transacao: Transacao, status: str) -> None:
        if transacao.status == status:
            return
        transacao.status = status
        transacao.save(update_fields=["status", "atualizado_em"])

    def _campos_atualizacao(self, campos: Iterable[str]) -> list[str]:
        return [*campos, "atualizado_em"]

    def _mapear_status(self, status: str | None) -> str:
        if status is None:
            return Transacao.Status.PENDENTE
        status = status.lower()
        if status in {"approved", "paid"}:
            return Transacao.Status.APROVADA
        if status in {"refunded", "cancelled"}:
            return Transacao.Status.ESTORNADA
        if status in {"rejected", "failed"}:
            return Transacao.Status.FALHOU
        return Transacao.Status.PENDENTE
