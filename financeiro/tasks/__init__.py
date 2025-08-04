from __future__ import annotations

import logging

from celery import shared_task  # type: ignore
from django.utils import timezone

from ..models import FinanceiroTaskLog
from ..services import metrics
from ..services.cobrancas import gerar_cobrancas

logger = logging.getLogger(__name__)


@shared_task
def gerar_cobrancas_mensais() -> None:
    """Gera cobranças mensais para associados ativos."""
    logger.info("Gerando cobranças mensais")
    inicio = timezone.now()
    status = "sucesso"
    detalhes = ""
    try:
        gerar_cobrancas()
    except Exception as exc:  # pragma: no cover - exceção não esperada
        logger.exception("Erro ao gerar cobranças: %s", exc)
        status = "erro"
        detalhes = str(exc)
        raise
    finally:
        elapsed = (timezone.now() - inicio).total_seconds()
        logger.info("Cobranças geradas em %.2fs", elapsed)
        metrics.cobrancas_total.inc()
        FinanceiroTaskLog.objects.create(
            nome_tarefa="gerar_cobrancas_mensais",
            status=status,
            detalhes=detalhes,
        )
