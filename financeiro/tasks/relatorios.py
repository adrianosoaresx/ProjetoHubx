from __future__ import annotations

import logging
import os
from datetime import datetime
from typing import Sequence

from celery import shared_task  # type: ignore
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage

from ..models import FinanceiroTaskLog
from ..services import metrics
from ..services.exportacao import exportar_para_arquivo
from ..services.relatorios import _base_queryset

logger = logging.getLogger(__name__)


@shared_task
def gerar_relatorio_async(
    token: str,
    fmt: str,
    *,
    centro: str | Sequence[str] | None = None,
    nucleo: str | None = None,
    inicio: str | None = None,
    fim: str | None = None,
    tipo: str | None = None,
    status: str | None = None,
) -> str:
    """Gera relatório financeiro em arquivo e salva no storage."""
    logger.info("Gerando relatório %s.%s", token, fmt)
    metrics.financeiro_tasks_total.inc()
    inicio_dt = datetime.fromisoformat(inicio) if inicio else None
    fim_dt = datetime.fromisoformat(fim) if fim else None
    qs_csv = _base_queryset(centro, nucleo, inicio_dt, fim_dt)
    if tipo == "receitas":
        qs_csv = qs_csv.filter(valor__gt=0)
    elif tipo == "despesas":
        qs_csv = qs_csv.filter(valor__lt=0)
    if status:
        qs_csv = qs_csv.filter(status=status)
    linhas = [
        [
            lanc.data_lancamento.date(),
            lanc.get_tipo_display(),
            float(lanc.valor),
            lanc.status,
            lanc.centro_custo.nome,
        ]
        for lanc in qs_csv
    ]
    headers = ["data", "categoria", "valor", "status", "centro de custo"]
    status_log = "sucesso"
    detalhes = ""
    path = ""
    tmp_name = ""
    try:
        tmp_name = exportar_para_arquivo(fmt, headers, linhas)
        with open(tmp_name, "rb") as f:
            content = ContentFile(f.read())
        path = default_storage.save(f"relatorios/{token}.{fmt}", content)
    except Exception as exc:  # pragma: no cover - erro inesperado
        logger.exception("Erro ao gerar relatório: %s", exc)
        status_log = "erro"
        detalhes = str(exc)
        raise
    finally:
        if tmp_name and os.path.exists(tmp_name):
            try:
                os.remove(tmp_name)
            except OSError:
                pass
        FinanceiroTaskLog.objects.create(
            nome_tarefa="gerar_relatorio_async",
            status=status_log,
            detalhes=detalhes or path,
        )
    return path
