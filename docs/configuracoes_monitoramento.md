# Monitoramento das Configurações de Conta

A API de configurações expõe métricas Prometheus para acompanhar a latência.
O histograma `configuracao_conta_api_latency_seconds` possui buckets em
`50ms, 100ms, 250ms, 500ms, 1s e 2s` e permite calcular o p95 da latência.

## Consulta PromQL

```
histogram_quantile(0.95, sum(rate(configuracao_conta_api_latency_seconds_bucket[5m])) by (le))
```

## Alerta

Exemplo de regra no Prometheus Alertmanager para disparar quando o p95
ultrapassar `100ms` por 5 minutos:

```
- alert: ConfiguracaoContaLatenciaAlta
  expr: histogram_quantile(0.95, sum(rate(configuracao_conta_api_latency_seconds_bucket[5m])) by (le)) > 0.1
  for: 5m
  labels:
    severity: warning
  annotations:
    summary: "Latência p95 do endpoint de configurações acima de 100ms"
```

Configure o Grafana para plotar a mesma expressão para visualizar a tendência
da latência ao longo do tempo.
