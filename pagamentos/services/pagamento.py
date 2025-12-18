from __future__ import annotations

import logging
import time
from typing import Any, Iterable

from django.conf import settings
from django.db import OperationalError, connections, transaction

from pagamentos import metrics
from pagamentos.exceptions import PagamentoInvalidoError
from pagamentos.models import Pedido, Transacao
from pagamentos.notifications import enviar_email_pagamento_aprovado
from pagamentos.providers.base import PaymentProvider

logger = logging.getLogger(__name__)


class PagamentoService:
    """Serviço de domínio para orquestrar operações de pagamento."""

    db_retry_delays = (0.1, 0.25, 0.5)

    def __init__(self, provider: PaymentProvider) -> None:
        self.provider = provider

    def iniciar_pagamento(
        self, pedido: Pedido, metodo: str, dados_pagamento: dict[str, Any] | None = None
    ) -> Transacao:
        """Cria a cobrança no provedor e registra a transação localmente."""

        if metodo not in Transacao.Metodo.values:
            raise PagamentoInvalidoError("Método inválido")

        try:
            resposta = self.provider.criar_cobranca(pedido, metodo, dados_pagamento)
        except Exception:
            metrics.pagamentos_erros_total.labels(fase="criacao", metodo=metodo).inc()
            logger.exception(
                "erro_criacao_cobranca",
                extra={"pedido_id": pedido.id, "metodo": metodo},
            )
            raise
        status = self._mapear_status(resposta.get("status"))
        external_id = str(resposta.get("id")) if resposta.get("id") else None

        with transaction.atomic():
            transacao = Transacao.objects.create(
                pedido=pedido,
                valor=pedido.valor,
                status=status,
                metodo=metodo,
                external_id=external_id,
                detalhes=resposta,
            )
            self._sincronizar_pedido(pedido, status, external_id)
        metrics.pagamentos_criados_total.labels(metodo=metodo).inc()
        if status == Transacao.Status.APROVADA:
            self._notificar_pagamento(transacao)
            metrics.pagamentos_aprovados_total.labels(metodo=metodo).inc()
        return transacao

    def confirmar_pagamento(self, transacao: Transacao) -> Transacao:
        """Consulta o provedor e sincroniza o status local."""

        try:
            resposta = self.provider.confirmar_pagamento(transacao)
        except Exception:
            metrics.pagamentos_erros_total.labels(fase="confirmacao", metodo=transacao.metodo).inc()
            logger.exception(
                "erro_confirmacao_pagamento",
                extra={"transacao_id": transacao.id, "external_id": transacao.external_id},
            )
            raise
        status = self._mapear_status(resposta.get("status"))
        transacao = self._atualizar_com_retry(
            transacao,
            status,
            resposta,
            provider_order_id=resposta.get("order_id"),
            fase="confirmacao",
        )
        return transacao

    def estornar_pagamento(self, transacao: Transacao) -> Transacao:
        """Delegar o estorno de pagamento ao provedor."""

        try:
            resposta = self.provider.estornar_pagamento(transacao)
        except Exception:
            metrics.pagamentos_erros_total.labels(fase="estorno", metodo=transacao.metodo).inc()
            logger.exception(
                "erro_estorno_pagamento",
                extra={"transacao_id": transacao.id, "external_id": transacao.external_id},
            )
            raise
        status = self._mapear_status(resposta.get("status") or Transacao.Status.ESTORNADA)
        transacao = self._atualizar_com_retry(
            transacao,
            status,
            resposta,
            provider_order_id=resposta.get("order_id"),
            fase="estorno",
        )
        metrics.pagamentos_estornados_total.labels(metodo=transacao.metodo).inc()
        return transacao

    def _atualizar_com_retry(
        self,
        transacao: Transacao,
        status: str,
        detalhes: dict | None,
        provider_order_id: str | None,
        fase: str,
    ) -> Transacao:
        last_error: Exception | None = None
        for tentativa, delay in enumerate((0.0, *self.db_retry_delays), start=1):
            if delay:
                time.sleep(delay)
            try:
                with transaction.atomic():
                    locked_transacao = self._lock_transacao(transacao)
                    self._atualizar_transacao(locked_transacao, status, detalhes)
                    self._sincronizar_pedido(
                        locked_transacao.pedido, status, provider_order_id
                    )
                    return locked_transacao
            except OperationalError as exc:
                last_error = exc
                logger.warning(
                    "pagamento_operational_retry",
                    extra={
                        "transacao_id": transacao.id,
                        "fase": fase,
                        "tentativa": tentativa,
                    },
                )
        if last_error:
            raise last_error
        return transacao

    def _lock_transacao(self, transacao: Transacao) -> Transacao:
        alias = transacao._state.db or "default"
        if not self._row_locking_enabled(alias):
            return transacao
        return (
            Transacao.objects.using(alias)
            .select_related("pedido")
            .select_for_update()
            .get(pk=transacao.pk)
        )

    def _row_locking_enabled(self, alias: str) -> bool:
        if not getattr(settings, "PAGAMENTOS_ROW_LOCKS_ENABLED", True):
            return False
        features = connections[alias].features
        has_select_for_update = getattr(features, "has_select_for_update", None)
        if has_select_for_update is not None:
            return bool(has_select_for_update)
        return bool(getattr(features, "supports_select_for_update", False))

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

    def _atualizar_transacao(self, transacao: Transacao, status: str, detalhes: dict | None = None) -> None:
        status_anterior = transacao.status
        atualizacoes = []
        if transacao.status != status:
            transacao.status = status
            atualizacoes.extend(["status", "atualizado_em"])
        if detalhes:
            transacao.detalhes = detalhes
            atualizacoes.append("detalhes")
        if atualizacoes:
            transacao.save(update_fields=list(dict.fromkeys(atualizacoes)))
        if status_anterior != Transacao.Status.APROVADA and status == Transacao.Status.APROVADA:
            self._notificar_pagamento(transacao)
            metrics.pagamentos_aprovados_total.labels(metodo=transacao.metodo).inc()

    def _campos_atualizacao(self, campos: Iterable[str]) -> list[str]:
        return [*campos, "atualizado_em"]

    def _mapear_status(self, status: str | None) -> str:
        if status is None:
            return Transacao.Status.PENDENTE
        status = status.lower()
        if status in {"approved", "paid", "completed", "captured"}:
            return Transacao.Status.APROVADA
        if status in {"refunded", "cancelled", "voided"}:
            return Transacao.Status.ESTORNADA
        if status in {"rejected", "failed", "declined"}:
            return Transacao.Status.FALHOU
        return Transacao.Status.PENDENTE

    def _notificar_pagamento(self, transacao: Transacao) -> None:
        try:
            enviar_email_pagamento_aprovado(transacao)
        except Exception:
            metrics.pagamentos_erros_total.labels(
                fase="notificacao", metodo=transacao.metodo
            ).inc()
            logger.exception(
                "erro_notificacao_pagamento",
                extra={"transacao_id": transacao.id, "pedido_id": transacao.pedido_id},
            )
