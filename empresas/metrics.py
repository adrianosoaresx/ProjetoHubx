from prometheus_client import Counter

empresas_favoritos_total = Counter(
    "empresas_favoritos_total",
    "Total de operações de favoritos em empresas",
    ["acao"],
)

empresas_restauradas_total = Counter(
    "empresas_restauradas_total",
    "Total de empresas restauradas",
)

empresas_purgadas_total = Counter(
    "empresas_purgadas_total",
    "Total de empresas purgadas",
)
