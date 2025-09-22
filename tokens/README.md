# Convites e códigos

O aplicativo `tokens` centraliza os fluxos de convites de acesso e dos códigos de
autenticação temporários utilizados em rotinas de 2FA. Ele oferece endpoints de
API e telas internas para que administradores criem convites, acompanhem seu
uso e auxiliem usuários que precisam gerar códigos para validação.

## Convites

### Criação via API

Os convites (`TokenAcesso`) podem ser emitidos pelo endpoint
`POST /api/tokens/tokens/`. Um exemplo mínimo de payload é:

```http
POST /api/tokens/tokens/
{
  "tipo_destino": "associado",
  "organizacao": 123,
  "data_expiracao": "2024-12-31"
}
```

A resposta contém o código gerado. Ele é exibido apenas uma vez no momento da
criação, portanto deve ser armazenado imediatamente pelo integrador.

### Validação

A validação pode ser feita por meio do endpoint
`GET /api/tokens/tokens/validate/?codigo=<codigo>`. Além de confirmar o status
atual do convite, a chamada registra logs de auditoria e incrementa as métricas
de uso.

### Uso

Uma vez validado, o convite pode ser consumido pelo endpoint
`POST /api/tokens/tokens/<id>/use/`. A requisição deve ser autenticada e o
convite precisa estar no estado `novo` para ser aceito.

### Revogação

Convites ativos podem ser revogados com
`POST /api/tokens/tokens/<codigo>/revogar/`. A operação registra os dados de quem
a executou, além do IP e do user agent informados.

## Códigos de autenticação

As views `POST /tokens/gerar-codigo/` e `POST /tokens/validar-codigo/` permitem
que usuários gerem e confirmem códigos temporários utilizados na autenticação
em duas etapas. Ambos os fluxos armazenam logs contendo IP, user agent e o
resultado da operação para posterior auditoria.

## Webhooks

Quando a configuração `TOKENS_WEBHOOK_URL` está definida, o sistema envia um
webhook para cada evento relevante de convites:

- `invite.created`: `{ "event": "invite.created", "id": "<token-id>", "code": "<codigo>" }`
- `invite.used`: `{ "event": "invite.used", "id": "<token-id>" }`
- `invite.revoked`: `{ "event": "invite.revoked", "id": "<token-id>" }`

Os eventos são assinados opcionalmente com o cabeçalho `X-Hubx-Signature` quando
`TOKEN_WEBHOOK_SECRET` está configurado.

## Métricas Prometheus

O módulo expõe métricas para monitorar convites, validações e webhooks:

- `tokens_invites_created_total`: total de convites criados.
- `tokens_invites_used_total`: total de convites utilizados.
- `tokens_invites_revoked_total`: total de convites revogados.
- `tokens_validation_fail_total`: total de falhas na validação de convites.
- `tokens_validation_latency_seconds`: histograma com a latência das validações.
- `tokens_rate_limited_total`: total de requisições bloqueadas por rate limit.
- `tokens_webhooks_sent_total`: webhooks entregues com sucesso.
- `tokens_webhooks_failed_total`: webhooks que falharam após todas as tentativas.
- `tokens_webhook_latency_seconds`: histograma da latência no envio de webhooks.

Exemplos de regras de alerta podem ser importados a partir de
`prometheus/tokens_alerts.yml`.
