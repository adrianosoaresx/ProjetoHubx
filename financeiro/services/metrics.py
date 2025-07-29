"""Prometheus metrics wrappers."""

from __future__ import annotations

from prometheus_client import Counter  # type: ignore

importacao_pagamentos_total = Counter("importacao_pagamentos_total", "Número total de lançamentos importados")
notificacoes_total = Counter("notificacoes_total", "Número total de notificações enviadas")
cobrancas_total = Counter("cobrancas_total", "Número total de cobranças geradas")
