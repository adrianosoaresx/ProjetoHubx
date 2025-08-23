from __future__ import annotations

import logging
from pathlib import Path

from celery import shared_task  # type: ignore
from django.contrib.auth import get_user_model
from django.utils import timezone

from notificacoes.services.notificacoes import enviar_para_usuario

from ..models import FinanceiroLog, FinanceiroTaskLog, ImportacaoPagamentos
from ..services import metrics
from ..services.auditoria import log_financeiro
from ..services.importacao import AlreadyProcessedError, ImportadorPagamentos

logger = logging.getLogger(__name__)


@shared_task
def importar_pagamentos_async(file_path: str, user_id: str, importacao_id: str) -> None:
    """Importa pagamentos de forma assíncrona."""
    logger.info("Iniciando importação de pagamentos %s", file_path)
    metrics.financeiro_tasks_total.inc()
    inicio = timezone.now()
    status = "sucesso"
    detalhes = ""
    try:
        service = ImportadorPagamentos(file_path)
        importacao = ImportacaoPagamentos.objects.get(pk=importacao_id)
        total, errors = service.process(idempotency_key=importacao.idempotency_key)
        log_path = Path(file_path).with_suffix(".log")
        if errors:
            log_path.write_text("\n".join(errors), encoding="utf-8")
            logger.error("Erros na importação: %s", errors)
        else:
            log_path.write_text("ok", encoding="utf-8")
        status_model = (
            ImportacaoPagamentos.Status.ERRO if errors else ImportacaoPagamentos.Status.CONCLUIDO
        )
        ImportacaoPagamentos.objects.filter(pk=importacao_id).update(
            arquivo=file_path,
            usuario_id=user_id,
            total_processado=total,
            erros=errors,
            status=status_model,
        )
        elapsed = (timezone.now() - inicio).total_seconds()
        logger.info("Importação concluída: %s registros em %.2fs", total, elapsed)
        metrics.importacao_pagamentos_total.inc(total)
        if errors:
            metrics.financeiro_importacoes_erros_total.inc()
        user = get_user_model().objects.filter(pk=user_id).first()
        log_financeiro(
            FinanceiroLog.Acao.IMPORTAR,
            user,
            {"arquivo": file_path, "total": total, "erros": errors},
            {"status": status_model},
        )
        if user:
            try:  # pragma: no branch - falha externa
                enviar_para_usuario(user, "importacao_pagamentos", {"total": total})
            except Exception as exc:  # pragma: no cover - integração externa
                logger.error("Falha ao notificar importação: %s", exc)
    except AlreadyProcessedError:
        ImportacaoPagamentos.objects.filter(pk=importacao_id).update(
            status=ImportacaoPagamentos.Status.CONCLUIDO
        )
        logger.info("Importação %s já processada", importacao_id)
        return
    except Exception as exc:  # pragma: no cover - exceção inesperada
        logger.exception("Erro na importação de pagamentos: %s", exc)
        ImportacaoPagamentos.objects.filter(pk=importacao_id).update(
            erros=[str(exc)], status=ImportacaoPagamentos.Status.ERRO
        )
        status = "erro"
        detalhes = str(exc)
        raise
    finally:
        FinanceiroTaskLog.objects.create(
            nome_tarefa="importar_pagamentos_async",
            status=status,
            detalhes=detalhes,
        )


@shared_task
def reprocessar_importacao_async(err_file_path: str, file_path: str) -> None:
    """Reprocessa importações corrigidas de forma assíncrona."""
    logger.info("Iniciando reprocessamento de importação %s", file_path)
    metrics.financeiro_tasks_total.inc()
    status = "sucesso"
    detalhes = ""
    try:
        service = ImportadorPagamentos(file_path)
        total, errors = service.process()
        log_path = Path(file_path).with_suffix(".log")
        if errors:
            log_path.write_text("\n".join(errors), encoding="utf-8")
            detalhes = "\n".join(errors)
            status = "erro"
            metrics.financeiro_importacoes_erros_total.inc()
        else:
            log_path.write_text("ok", encoding="utf-8")
            Path(err_file_path).unlink(missing_ok=True)
        logger.info("Reprocessamento concluído: %s registros", total)
        metrics.importacao_pagamentos_total.inc(total)
    except Exception as exc:  # pragma: no cover - exceção inesperada
        logger.exception("Erro no reprocessamento de importação: %s", exc)
        status = "erro"
        detalhes = str(exc)
        raise
    finally:
        FinanceiroTaskLog.objects.create(
            nome_tarefa="reprocessar_importacao_async",
            status=status,
            detalhes=detalhes,
        )
