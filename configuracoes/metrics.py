from __future__ import annotations

from prometheus_client import Counter, Summary  # type: ignore

config_cache_hits_total = Counter(
    "configuracao_conta_cache_hits_total", "Total de hits de cache para configurações de conta"
)
config_cache_misses_total = Counter(
    "configuracao_conta_cache_misses_total", "Total de misses de cache para configurações de conta"
)
config_get_latency_seconds = Summary(
    "configuracao_conta_get_latency_seconds", "Latência para obter configuração de conta"
)
config_api_latency_seconds = Summary(
    "configuracao_conta_api_latency_seconds", "Latência das requisições da API de ConfiguracaoConta", ["method"]
)
