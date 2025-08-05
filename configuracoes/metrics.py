from __future__ import annotations

from prometheus_client import Counter, Histogram, Summary  # type: ignore

config_cache_hits_total = Counter(
    "configuracao_conta_cache_hits_total", "Total de hits de cache para configurações de conta"
)
config_cache_misses_total = Counter(
    "configuracao_conta_cache_misses_total", "Total de misses de cache para configurações de conta"
)
config_get_latency_seconds = Summary(
    "configuracao_conta_get_latency_seconds", "Latência para obter configuração de conta"
)
config_api_latency_seconds = Histogram(
    "configuracao_conta_api_latency_seconds",
    "Latência das requisições da API de ConfiguracaoConta",
    ["method"],
    buckets=(0.05, 0.1, 0.25, 0.5, 1, 2),
)
