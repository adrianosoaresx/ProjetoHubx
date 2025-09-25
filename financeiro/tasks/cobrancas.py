from __future__ import annotations

import logging

from celery import shared_task  # type: ignore
from django.utils import timezone

from ..services.cobrancas import gerar_cobrancas

logger = logging.getLogger(__name__)


@shared_task
def gerar_cobrancas_mensais() -> None:
    """Gera cobranças mensais de forma recorrente."""
    logger.info("Gerando cobranças mensais")
    inicio = timezone.now()
    try:
        gerar_cobrancas()
    except Exception as exc:  # pragma: no cover - exceção não esperada
        logger.exception("Erro ao gerar cobranças: %s", exc)
        raise
    finally:
        logger.info("Cobranças geradas em %s", timezone.now() - inicio)
