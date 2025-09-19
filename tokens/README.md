# Tokens

O app `tokens` concentra fluxos de convites, códigos de autenticação e automações de 2FA. A emissão de tokens de API para integrações externas foi descontinuada; as páginas do painel e os endpoints REST associados foram removidos. Os serviços internos `generate_token`, `revoke_token` e `rotate_token` permanecem disponíveis apenas para rotinas automatizadas, preservando as integrações legadas (webhooks, métricas e tarefas agendadas).

## Webhooks

Quando `TOKENS_WEBHOOK_URL` está configurado, a aplicação envia notificações HTTP para os principais eventos:

- `invite.created`: `{ "event": "invite.created", "id": "<token-id>", "code": "<token-code>" }`
- `invite.used`: `{ "event": "invite.used", "id": "<token-id>" }`
- `invite.revoked`: `{ "event": "invite.revoked", "id": "<token-id>" }`
- `created`: `{ "event": "created", "id": "<token-id>", "token": "<token-hash>" }` (legado para tokens de API)
- `revoked`: `{ "event": "revoked", "id": "<token-id>" }`
- `rotated`: `{ "event": "rotated", "id": "<old-token-id>", "new_id": "<new-token-id>" }`

O campo `token` contém o hash SHA-256 do valor bruto, nunca o token original.

## Tarefas periódicas

O Celery Beat executa tarefas de manutenção relacionadas aos tokens:

- `revogar_tokens_expirados`: revoga tokens de API expirados e registra o evento.
- `remover_logs_antigos`: remove logs com mais de um ano.
- `rotacionar_tokens_proximos_da_expiracao`: substitui tokens de API próximos da expiração.
- `reenviar_webhooks_pendentes`: tenta reenviar notificações que falharam anteriormente.

## Métricas Prometheus

O módulo expõe métricas para monitorar convites, webhooks e tokens de API legados:

- `tokens_invites_created_total`: convites gerados.
- `tokens_invites_used_total`: convites utilizados.
- `tokens_invites_revoked_total`: convites revogados.
- `tokens_validation_fail_total`: falhas na validação de convites.
- `tokens_rate_limited_total`: requisições bloqueadas por rate limit.
- `tokens_webhooks_sent_total`: webhooks enviados com sucesso.
- `tokens_webhooks_failed_total`: falhas no envio de webhooks.
- `tokens_webhook_latency_seconds`: histograma de latência dos webhooks.
- `tokens_api_tokens_created_total`: tokens de API gerados (legado).
- `tokens_api_tokens_revoked_total`: tokens de API revogados (legado).
- `tokens_api_tokens_rotated_total`: tokens de API rotacionados (legado).
- `tokens_api_latency_seconds`: latência de operações na API de convites.
- `tokens_validation_latency_seconds`: latência na validação de convites.

Exemplos de regras de alerta podem ser importados a partir de `prometheus/tokens_alerts.yml`.
