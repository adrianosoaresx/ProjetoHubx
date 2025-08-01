
from prometheus_client import Counter, Gauge  # type: ignore

notificacoes_enviadas_total = Counter(
    "notificacoes_enviadas_total",
    "Número de notificações enviadas",
    ["canal"],
)

notificacoes_falhadas_total = Counter(
    "notificacoes_falhadas_total",
    "Número de notificações falhadas",
    ["canal"],
)

templates_total = Gauge("templates_total", "Total de templates ativos")

