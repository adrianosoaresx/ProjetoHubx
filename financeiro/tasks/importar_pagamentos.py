from __future__ import annotations

import logging
from pathlib import Path

from celery import shared_task

from ..services.importacao import ImportadorPagamentos

logger = logging.getLogger(__name__)


@shared_task
def importar_pagamentos_async(file_path: str, user_id: str) -> None:
    """Importa pagamentos de forma assíncrona."""
    logger.info("Iniciando importação de pagamentos %s", file_path)
    service = ImportadorPagamentos(file_path)
    errors = service.process()
    log_path = Path(file_path).with_suffix(".log")
    if errors:
        log_path.write_text("\n".join(errors), encoding="utf-8")
        logger.error("Erros na importação: %s", errors)
    else:
        log_path.write_text("ok", encoding="utf-8")
    logger.info("Importação concluída")
    # metrics.import_payments_total.inc()  # Exemplo de métrica Prometheus
