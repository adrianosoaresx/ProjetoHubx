from prometheus_client import Counter  # type: ignore

convites_gerados_total = Counter(
    "convites_gerados_total",
    "Total de convites de núcleo gerados",
)

convites_usados_total = Counter(
    "convites_usados_total",
    "Total de convites de núcleo utilizados",
)

membros_suspensos_total = Counter(
    "membros_suspensos_total",
    "Total de suspensões de membros em núcleos",
)

