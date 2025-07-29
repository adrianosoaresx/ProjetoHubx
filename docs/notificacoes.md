# App de Notificações

Este módulo centraliza o envio de mensagens via e-mail, push e WhatsApp.

## Modelos

- `NotificationTemplate` – define mensagens para cada canal.
- `UserNotificationPreference` – guarda preferências do usuário por canal.
- `NotificationLog` – histórico de envios.

## Uso

1. Cadastre templates no admin (`/admin/notificacoes/notificationtemplate/`).
2. No código, chame `notificacoes.services.notificacoes.enviar_para_usuario` passando o usuário, o código do template e um `context`.

Envios são processados de forma assíncrona pelo Celery.

## Configurações

```python
NOTIFICATIONS_EMAIL_API_URL = os.getenv("NOTIFICATIONS_EMAIL_API_URL", "")
NOTIFICATIONS_EMAIL_API_KEY = os.getenv("NOTIFICATIONS_EMAIL_API_KEY", "")
NOTIFICATIONS_PUSH_API_URL = os.getenv("NOTIFICATIONS_PUSH_API_URL", "")
NOTIFICATIONS_PUSH_API_KEY = os.getenv("NOTIFICATIONS_PUSH_API_KEY", "")
NOTIFICATIONS_WHATSAPP_API_URL = os.getenv("NOTIFICATIONS_WHATSAPP_API_URL", "")
NOTIFICATIONS_WHATSAPP_API_KEY = os.getenv("NOTIFICATIONS_WHATSAPP_API_KEY", "")
NOTIFICATIONS_ENABLED = True
```

Para adicionar novos canais, crie funções em `notifications_client.py` e atualize `enviar_notificacao_async`.
