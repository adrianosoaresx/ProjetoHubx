from __future__ import annotations

from prometheus_client import Counter, Histogram

membros_notificados_total = Counter(
    "organizacoes_membros_notificados_total",
    "Total de notificações enviadas aos membros de organizações",
)

membros_notificacao_latency = Histogram(
    "organizacoes_membros_notificacao_latency_seconds",
    "Tempo para enviar notificações aos membros de organizações",
)
