from __future__ import annotations

import logging
from datetime import datetime
from typing import Sequence

from celery import shared_task  # type: ignore

from ..models import FinanceiroTaskLog
from ..services import metrics
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
    """Relatórios em arquivo foram descontinuados."""
    logger.info("Tentativa de gerar relatório %s.%s bloqueada", token, fmt)
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
    FinanceiroTaskLog.objects.create(
        nome_tarefa="gerar_relatorio_async",
        status="erro",
        detalhes="formato indisponível",
    )
    raise RuntimeError("formato indisponível")
