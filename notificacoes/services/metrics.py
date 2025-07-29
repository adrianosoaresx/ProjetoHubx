from prometheus_client import Counter  # type: ignore

notificacoes_enviadas_total = Counter("notificacoes_enviadas_total", "Número total de notificações enviadas")
