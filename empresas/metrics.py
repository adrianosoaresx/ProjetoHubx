from prometheus_client import Counter

empresas_favoritos_total = Counter(
    "empresas_favoritos_total",
    "Total de operações de favoritos em empresas",
    ["acao"],
)
