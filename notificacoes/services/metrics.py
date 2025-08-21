
from prometheus_client import Counter, Gauge, Histogram  # type: ignore

notificacoes_enviadas_total = Counter(
    "notificacoes_enviadas_total",
    "Número de notificações enviadas",
    ["canal"],
)

notificacoes_falhadas_total = Counter(
    "notificacoes_falhadas_total",
    "Número de notificações com falha",
    ["canal"],
)

notificacao_task_duration_seconds = Histogram(
    "notificacao_task_duration_seconds",
    "Duração das tarefas de notificação",
    ["task"],
    buckets=(0.1, 0.5, 1, 2, 5),
)


templates_total = Gauge(
    "templates_total", "Total de templates de notificação ativos"
)

