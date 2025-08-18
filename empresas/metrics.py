from prometheus_client import Counter, Gauge

empresas_favoritos_total = Gauge(
    "empresas_favoritos_total",
    "Total de favoritos em empresas",
)

empresas_restauradas_total = Counter(
    "empresas_restauradas_total",
    "Total de empresas restauradas",
)

empresas_purgadas_total = Counter(
    "empresas_purgadas_total",
    "Total de empresas purgadas",
)
