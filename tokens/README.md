# Tokens

Este aplicativo gerencia convites de acesso, códigos de autenticação e o envio de webhooks
relacionados.

## Convites via API

As integrações podem gerar e administrar convites utilizando o endpoint `/api/tokens/`.
Algumas operações disponíveis:

- **POST `/api/tokens/`**: cria um convite e retorna os dados do `TokenAcesso` junto com o
  código secreto (apenas na resposta de criação).
- **GET `/api/tokens/validate?codigo=<codigo>`**: valida um código sem consumi-lo.
- **POST `/api/tokens/<id>/use/`**: marca o convite como utilizado.
- **POST `/api/tokens/<codigo>/revogar/`**: revoga o convite informado.

Cada operação registra entradas em `TokenUsoLog`, preservando IP e *user agent* do cliente.

## Webhooks

Quando `TOKENS_WEBHOOK_URL` é configurado, os seguintes eventos são enviados de forma assíncrona:

- `invite.created`: convite gerado com sucesso (inclui o código).
- `invite.used`: convite utilizado.
- `invite.revoked`: convite revogado.

Os envios utilizam o segredo `TOKEN_WEBHOOK_SECRET`, quando presente, para assinar as mensagens
via `X-Hubx-Signature` (SHA-256).

## Tarefas periódicas

O módulo fornece tarefas Celery para manutenção:

- `remover_logs_antigos`: remove registros de uso (`TokenUsoLog`) com mais de um ano.
- `reenviar_webhooks_pendentes`: reenvia eventos armazenados em `TokenWebhookEvent` após falhas.

## Métricas Prometheus

As seguintes métricas estão disponíveis em `tokens/metrics.py`:

- `tokens_invites_created_total`
- `tokens_invites_used_total`
- `tokens_invites_revoked_total`
- `tokens_validation_fail_total`
- `tokens_rate_limited_total`
- `tokens_api_latency_seconds`
- `tokens_validation_latency_seconds`
- `tokens_webhooks_sent_total`
- `tokens_webhooks_failed_total`
- `tokens_webhook_latency_seconds`

Essas métricas permitem acompanhar o fluxo de convites, a efetividade dos webhooks e a saúde das
operações do módulo.
