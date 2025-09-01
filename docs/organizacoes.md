# Organizações

Este módulo gerencia entidades de organizações.

### API

O endpoint `GET /api/organizacoes/` aceita o parâmetro de consulta `inativa` para
definir se organizações inativas devem ser incluídas na resposta. Os tokens a
seguir são reconhecidos (case-insensitive):

- Valores verdadeiros: `1`, `true`, `t`, `yes`
- Valores falsos: `0`, `false`, `f`, `no`

Quando o parâmetro não é informado, apenas organizações ativas são retornadas.

### Métricas

Métricas Prometheus disponíveis em `organizacoes.metrics`:

- `organizacoes_membros_notificados_total`: Total de notificações enviadas aos membros de organizações.
- `organizacoes_membros_notificacao_latency_seconds`: Tempo para enviar notificações aos membros de organizações.
- `organizacoes_list_latency_seconds`: Latência das requisições de listagem de organizações.
- `organizacoes_detail_latency_seconds`: Latência das requisições de detalhe de organizações.
