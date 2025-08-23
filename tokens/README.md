# Tokens de API

Este módulo fornece autenticação via **tokens de API** para integrações externas.

## Uso

### Geração

```http
POST /api/api-tokens/
{
  "scope": "read",  // read, write ou admin
  "expires_in": 30    // dias
}
```

O valor do token é retornado apenas uma vez na criação. Guarde-o com segurança.

### Autenticação

Envie o cabeçalho:

```
Authorization: Bearer <token>
```

### Revogação

```http
DELETE /api/api-tokens/<id>/
```

Revogações feitas via API registram o IP e o *user agent* do cliente.
Revogações automáticas, executadas pela tarefa periódica
`revogar_tokens_expirados`, registram o IP `0.0.0.0` e o *user agent*
`task:revogar_tokens_expirados`.

### Rotação

```http
POST /api/api-tokens/<id>/rotate/
```

Revoga o token antigo e retorna um novo valor.

### Segurança

- Utilize sempre HTTPS.
- Revogue tokens comprometidos imediatamente.
- A validade máxima recomendada é de 1 ano.

## Tarefas periódicas

O Celery Beat executa diariamente duas tarefas de manutenção:

- `revogar_tokens_expirados`: revoga automaticamente tokens cuja data de expiração já passou.
- `remover_logs_antigos`: limpa logs de uso com mais de um ano.

Ambas são agendadas para rodar todos os dias à meia-noite.

## Métricas Prometheus

O módulo expõe métricas para monitorar o envio de webhooks:

- `tokens_webhooks_sent_total`: total de webhooks enviados com sucesso.
- `tokens_webhooks_failed_total`: total de webhooks que falharam após todas as tentativas.
- `tokens_webhook_latency_seconds`: histograma da latência do envio de webhooks.

Exemplos de regras de alerta podem ser importados a partir de `prometheus/tokens_alerts.yml`.

