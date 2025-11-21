# Monitoramento de Pagamentos

As métricas expostas pelo módulo `pagamentos` permitem acompanhar volume de cobranças, aprovações e falhas no Grafana.

## Métricas Prometheus

- `pagamentos_criados_total{metodo}` – contador de cobranças iniciadas (Pix, card, boleto).
- `pagamentos_aprovados_total{metodo}` – total de pagamentos aprovados.
- `pagamentos_estornados_total{metodo}` – estornos ou cancelamentos confirmados.
- `pagamentos_erros_total{fase,metodo}` – falhas nas fases de criação, confirmação, estorno ou notificação.

## Sugestão de painéis no Grafana

1. **Volume diário por método**
   - Query: `sum by (metodo)(increase(pagamentos_criados_total[1d]))`
   - Visualização: Bar chart agrupado por método.

2. **Taxa de aprovação**
   - Query: `sum(increase(pagamentos_aprovados_total[1h])) / sum(increase(pagamentos_criados_total[1h]))`
   - Formatar como percentual.

3. **Falhas e erros por fase**
   - Query: `sum by (fase)(increase(pagamentos_erros_total[30m]))`
   - Exibir em tabela e gráfico de linhas.

4. **Estornos acumulados**
   - Query: `sum by (metodo)(increase(pagamentos_estornados_total[7d]))`
   - Útil para auditoria semanal.

Importe estas consultas em um dashboard e aplique filtros por `metodo` para identificar gargalos específicos (ex.: somente boletos).
