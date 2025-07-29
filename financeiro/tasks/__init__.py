from __future__ import annotations

import logging

from celery import shared_task

from ..services.cobrancas import gerar_cobrancas
from ..services import metrics
from django.utils import timezone

logger = logging.getLogger(__name__)


@shared_task
def gerar_cobrancas_mensais() -> None:
    """Gera cobranças mensais para associados ativos."""
    logger.info("Gerando cobranças mensais")
    inicio = timezone.now()
    gerar_cobrancas()
    elapsed = (timezone.now() - inicio).total_seconds()
    logger.info("Cobranças geradas em %.2fs", elapsed)
    metrics.cobrancas_total.inc()
