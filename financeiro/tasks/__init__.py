from __future__ import annotations

from celery import shared_task

from ..services.cobrancas import gerar_cobrancas


@shared_task
def gerar_cobrancas_mensais() -> None:
    """Gera cobranças mensais para associados ativos."""
    gerar_cobrancas()
