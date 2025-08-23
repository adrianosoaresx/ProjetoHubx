# Monitoramento de Webhooks de Tokens

A aplicação expõe métricas Prometheus para acompanhar o envio de webhooks dos tokens.

- `tokens_webhooks_sent_total`: total de webhooks enviados com sucesso.
- `tokens_webhooks_failed_total`: total de webhooks que falharam após todas as tentativas.
- `tokens_webhook_latency_seconds`: histograma da latência do envio de webhooks.

## Consulta PromQL

```
histogram_quantile(0.95, sum(rate(tokens_webhook_latency_seconds_bucket[5m])) by (le))
```

## Alertas

O arquivo `prometheus/tokens_alerts.yml` define regras de alerta para falhas e latência elevada.

### Importar no Grafana

1. No Grafana, acesse **Alerting → Alert rules → Import**.
2. Envie o arquivo `prometheus/tokens_alerts.yml`.
3. Confirme a fonte de dados Prometheus e salve.
