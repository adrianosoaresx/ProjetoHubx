# Métricas de Configurações

As operações de leitura de preferências utilizam cache e expõem métricas Prometheus:

- `configuracao_conta_cache_hits_total` e `configuracao_conta_cache_misses_total` – contadores de hits/misses.
- `configuracao_conta_get_latency_seconds` – tempo de obtenção das preferências.
- `configuracao_conta_api_latency_seconds{method="<VERBO>"}` – latência das rotas de API.

As métricas permitem acompanhar a meta de leitura p95 ≤ 100ms.
