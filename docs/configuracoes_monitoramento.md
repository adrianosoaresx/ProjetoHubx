# Monitoramento das Configurações de Conta

A API de configurações expõe métricas Prometheus para acompanhar a latência.
O histograma `configuracao_conta_api_latency_seconds` possui buckets em
`50ms, 100ms, 250ms, 500ms, 1s e 2s` e permite calcular o p95 da latência.

## Consulta PromQL

```
histogram_quantile(0.95, sum(rate(configuracao_conta_api_latency_seconds_bucket[5m])) by (le))
```

## Alertas

O arquivo `prometheus/configuracoes_alerts.yml` define uma regra que dispara
quando o p95 ultrapassa `100ms` por 5 minutos.

```
groups:
  - name: configuracoes
    rules:
      - alert: ConfiguracaoContaLatenciaAlta
        expr: histogram_quantile(0.95, sum(rate(configuracao_conta_api_latency_seconds_bucket[5m])) by (le)) > 0.1
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Latência p95 do endpoint de configurações acima de 100ms"
```

### Importar no Grafana

1. No Grafana, acesse **Alerting → Alert rules → Import**.
2. Envie o arquivo `prometheus/configuracoes_alerts.yml`.
3. Confirme a fonte de dados Prometheus e salve.

### Testar localmente

1. Adicione o arquivo ao `prometheus.yml` com:

   ```yaml
   rule_files:
     - configuracoes_alerts.yml
   ```

2. Execute Prometheus e Alertmanager usando Docker:

   ```bash
   docker run --rm -p 9090:9090 -v $(pwd)/prometheus:/etc/prometheus prom/prometheus
   docker run --rm -p 9093:9093 -v $(pwd)/prometheus:/etc/prometheus prom/alertmanager
   ```

Configure o Grafana para plotar a mesma expressão para visualizar a tendência
da latência ao longo do tempo.
