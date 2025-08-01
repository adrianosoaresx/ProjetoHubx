from __future__ import annotations

import logging
from pathlib import Path

from celery import shared_task  # type: ignore
from django.utils import timezone

from ..models import ImportacaoPagamentos
from ..services import metrics
from ..services.importacao import ImportadorPagamentos

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
    ImportacaoPagamentos.objects.create(
        arquivo=file_path,
        usuario_id=user_id,
        total_processado=total,
        erros=errors,
    )
    elapsed = (timezone.now() - inicio).total_seconds()
    logger.info("Importação concluída: %s registros em %.2fs", total, elapsed)
    metrics.importacao_pagamentos_total.inc(total)
