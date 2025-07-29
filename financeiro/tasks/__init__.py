from __future__ import annotations

import logging

from celery import shared_task

from ..services.cobrancas import gerar_cobrancas

logger = logging.getLogger(__name__)


@shared_task
def gerar_cobrancas_mensais() -> None:
    """Gera cobranças mensais para associados ativos."""
    logger.info("Gerando cobranças mensais")
    gerar_cobrancas()
    logger.info("Cobranças geradas")
    # metrics.cobrancas_total.inc()  # Exemplo de métrica Prometheus
