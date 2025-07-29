from __future__ import annotations

import logging
from pathlib import Path

from celery import shared_task
from django.utils import timezone

from ..services.importacao import ImportadorPagamentos
from ..services import metrics

logger = logging.getLogger(__name__)


@shared_task
def importar_pagamentos_async(file_path: str, user_id: str) -> None:
    """Importa pagamentos de forma assíncrona."""
    logger.info("Iniciando importação de pagamentos %s", file_path)
    inicio = timezone.now()
    service = ImportadorPagamentos(file_path)
    total, errors = service.process()
    log_path = Path(file_path).with_suffix(".log")
    if errors:
        log_path.write_text("\n".join(errors), encoding="utf-8")
        logger.error("Erros na importação: %s", errors)
    else:
        log_path.write_text("ok", encoding="utf-8")
    elapsed = (timezone.now() - inicio).total_seconds()
    logger.info("Importação concluída: %s registros em %.2fs", total, elapsed)
    metrics.import_payments_total.inc(total)
