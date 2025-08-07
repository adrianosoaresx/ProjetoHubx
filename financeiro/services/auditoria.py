from __future__ import annotations

from typing import Any

from ..models import FinanceiroLog


def log_financeiro(
    acao: str,
    usuario,
    dados_anteriores: dict[str, Any] | None = None,
    dados_novos: dict[str, Any] | None = None,
) -> None:
    """Cria um registro de auditoria no módulo financeiro."""
    FinanceiroLog.objects.create(
        usuario=usuario,
        acao=acao,
        dados_anteriores=dados_anteriores or {},
        dados_novos=dados_novos or {},
    )
