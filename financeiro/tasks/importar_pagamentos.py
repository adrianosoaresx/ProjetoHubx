from __future__ import annotations

import logging
from pathlib import Path

from celery import shared_task  # type: ignore
from django.contrib.auth import get_user_model
from django.utils import timezone

from notificacoes.services.notificacoes import enviar_para_usuario

from ..models import ImportacaoPagamentos
from ..services import metrics
from ..services.importacao import ImportadorPagamentos


def executar_importacao(file_path: str, user_id: str, importacao_id: str) -> tuple[int, list[str], str]:
    """Processa o arquivo de importação atualizando o registro de controle."""

    service = ImportadorPagamentos(file_path)
    total, errors = service.process()
    log_path = Path(file_path).with_suffix(".log")
    if errors:
        log_path.write_text("\n".join(errors), encoding="utf-8")
    else:
        log_path.write_text("ok", encoding="utf-8")
    status_model = ImportacaoPagamentos.Status.ERRO if errors else ImportacaoPagamentos.Status.CONCLUIDO
    ImportacaoPagamentos.objects.filter(pk=importacao_id).update(
        arquivo=file_path,
        usuario_id=user_id,
        total_processado=total,
        erros=errors,
        status=status_model,
    )
    return total, errors, status_model

logger = logging.getLogger(__name__)


@shared_task
def importar_pagamentos_async(file_path: str, user_id: str, importacao_id: str) -> None:
    """Importa pagamentos de forma assíncrona."""
    logger.info("Iniciando importação de pagamentos %s", file_path)
    metrics.financeiro_tasks_total.inc()
    inicio = timezone.now()
    try:
        total, errors, status_model = executar_importacao(file_path, user_id, importacao_id)
        elapsed = (timezone.now() - inicio).total_seconds()
        logger.info("Importação concluída: %s registros em %.2fs", total, elapsed)
        metrics.importacao_pagamentos_total.inc(total)
        if errors:
            metrics.financeiro_importacoes_erros_total.inc()
            logger.error("Erros na importação: %s", errors)
        user = get_user_model().objects.filter(pk=user_id).first()
        if user:
            try:  # pragma: no branch - falha externa
                enviar_para_usuario(user, "importacao_pagamentos", {"total": total})
            except Exception as exc:  # pragma: no cover - integração externa
                logger.error("Falha ao notificar importação: %s", exc)
    except Exception as exc:  # pragma: no cover - exceção inesperada
        logger.exception("Erro na importação de pagamentos: %s", exc)
        ImportacaoPagamentos.objects.filter(pk=importacao_id).update(
            erros=[str(exc)], status=ImportacaoPagamentos.Status.ERRO
        )
        raise


@shared_task
def reprocessar_importacao_async(err_file_path: str, file_path: str) -> None:
    """Reprocessa importações corrigidas de forma assíncrona."""
    logger.info("Iniciando reprocessamento de importação %s", file_path)
    metrics.financeiro_tasks_total.inc()
    try:
        service = ImportadorPagamentos(file_path)
        total, errors = service.process()
        log_path = Path(file_path).with_suffix(".log")
        if errors:
            log_path.write_text("\n".join(errors), encoding="utf-8")
            metrics.financeiro_importacoes_erros_total.inc()
        else:
            log_path.write_text("ok", encoding="utf-8")
            Path(err_file_path).unlink(missing_ok=True)
        logger.info("Reprocessamento concluído: %s registros", total)
        metrics.importacao_pagamentos_total.inc(total)
    except Exception as exc:  # pragma: no cover - exceção inesperada
        logger.exception("Erro no reprocessamento de importação: %s", exc)
        raise
