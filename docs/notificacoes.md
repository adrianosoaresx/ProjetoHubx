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

### Serviço `enviar_para_usuario`

```python
from notificacoes.services.notificacoes import enviar_para_usuario

enviar_para_usuario(user, "codigo_do_template", {"nome": "Ana"})
```

Parâmetros:

- `user`: instância de usuário destino.
- `template_codigo`: código do `NotificationTemplate` ativo.
- `context`: dicionário usado para renderizar assunto e corpo.

Exceções:

- `ValueError` caso o template não exista ou esteja inativo.

Se todos os canais preferidos do usuário estiverem desabilitados, um `NotificationLog` é criado com status **FALHA** e nenhum envio é disparado.

Templates básicos já estão cadastrados via migração, incluindo `password_reset`,
`email_confirmation`, `cobranca_pendente` e `inadimplencia`. Outros códigos
podem ser adicionados conforme a necessidade de novos avisos.

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
