"""Prometheus metrics wrappers."""

from __future__ import annotations

from prometheus_client import Counter  # type: ignore

importacao_pagamentos_total = Counter(
    "importacao_pagamentos_total",
    "Número total de lançamentos importados",
)
notificacoes_total = Counter(
    "notificacoes_total", "Número total de notificações enviadas"
)
notificacoes_inadimplencia_total = Counter(
    "notificacoes_inadimplencia_total",
    "Número total de notificações de inadimplência enviadas",
)
cobrancas_total = Counter(
    "cobrancas_total", "Número total de cobranças geradas"
)
financeiro_cobrancas_total = Counter(
    "financeiro_cobrancas_total", "Cobranças recorrentes criadas"
)

# Novas métricas de observabilidade do módulo financeiro
financeiro_importacoes_total = Counter(
    "financeiro_importacoes_total", "Total de importações iniciadas"
)
financeiro_importacoes_erros_total = Counter(
    "financeiro_importacoes_erros_total",
    "Total de importações concluídas com erros",
)
financeiro_relatorios_total = Counter(
    "financeiro_relatorios_total", "Número de relatórios gerados"
)
financeiro_tasks_total = Counter(
    "financeiro_tasks_total", "Execuções de tarefas Celery do módulo"
)
