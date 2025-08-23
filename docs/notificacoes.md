# App de Notificações

Este módulo centraliza o envio de mensagens via e-mail, push e WhatsApp. Todos os modelos usam chaves UUID e herdam `TimeStampedModel`.
Para envio de WhatsApp é utilizada a API do Twilio; configure as variáveis
`TWILIO_SID`, `TWILIO_TOKEN` e `TWILIO_WHATSAPP_FROM` e certifique-se de instalar o pacote.

## Modelos

- `NotificationTemplate` – define mensagens para cada canal e possui campos `created_at`/`updated_at`/`deleted`.
- `UserNotificationPreference` – guarda preferências do usuário por canal e as frequências (`frequencia_email`, `frequencia_whatsapp`).
- `NotificationLog` – histórico de envios com status imutável (`pendente`, `enviada`, `falha`).

## Uso

1. Cadastre templates no admin (`/admin/notificacoes/notificationtemplate/`).
2. No código, chame `notificacoes.services.notificacoes.enviar_para_usuario` passando o usuário, o código do template e um `context`.

Envios são processados de forma assíncrona pelo Celery.

### Serviço `enviar_para_usuario`

```python
from notificacoes.services.notificacoes import enviar_para_usuario

enviar_para_usuario(user, "codigo_do_template", {"nome": "Ana"})
```

Parâmetros:

- `user`: instância de usuário destino.
- `template_codigo`: código do `NotificationTemplate`.
- `context`: dicionário usado para renderizar assunto e corpo.

Exceções:


- `ValueError` caso o template não exista ou tenha sido removido.


Se todos os canais preferidos do usuário estiverem desabilitados, um `NotificationLog` é criado com status **FALHA** e nenhum envio é disparado.

### Endpoints REST

- `GET /api/notificacoes/templates/` – lista templates (staff cria/edita).
- `GET/PUT /api/notificacoes/preferencias/` – preferências do usuário autenticado.
- `GET /api/notificacoes/logs/` – histórico do próprio usuário.
- `POST /api/notificacoes/enviar/` – dispara uma notificação com `user_id`, `template_codigo` e `contexto`.
- `PATCH /api/notificacoes/logs/<id>/` – marca uma notificação como lida.

### Métricas

Métricas Prometheus disponíveis em `notificacoes.services.metrics`:
`notificacoes_enviadas_total`, `notificacoes_falhadas_total` (por canal),
`notificacao_task_duration_seconds` e `templates_total`. Consulte o endpoint
`/metrics`.

> ⚠️ Envio via WhatsApp está em fase de testes e pode atuar apenas como _stub_.
