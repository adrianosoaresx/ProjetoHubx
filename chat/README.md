# Chat API

Módulo responsável pela comunicação em tempo real da plataforma. Os
recursos são expostos via REST e WebSocket e dependem de Redis,
Celery e Django Channels.

## Entidades

- **ChatChannel** – canal de conversa associado a um contexto (núcleo, evento,
  organização ou privado).
- **ChatParticipant** – relação de usuários com o canal, indicando
  proprietários e administradores.
- **ChatMessage** – mensagens enviadas no canal, com suporte a texto,
  arquivos e reações.
- **RelatorioChatExport** – registro de solicitações de exportação de
  histórico.

## Fluxo de camadas

```mermaid
flowchart LR
    Models --> Services --> ViewsAPI --> Consumers --> Tasks
```

## API REST

Endpoints REST para gerenciamento de canais e mensagens. Requer
autenticação via token JWT ou sessão.

## Exemplo de criação de canal

```http
POST /api/chat/channels/
Content-Type: application/json

{
  "contexto_tipo": "privado",
  "titulo": "Bate-papo"
}
```

## Listar mensagens de um canal

```http
GET /api/chat/channels/<id>/messages/
Authorization: Bearer <token>
```

Parâmetros opcionais:

- `desde=<timestamp>` – mensagens a partir de uma data/hora.
- `ate=<timestamp>` – mensagens até uma data/hora.

### Exportar histórico

```http
GET /api/chat/channels/<id>/export/?formato=csv
```

A chamada cria um `RelatorioChatExport` e, após processamento assíncrono,
disponibiliza um arquivo JSON ou CSV com as mensagens visíveis.

## WebSocket

Conexão:

```
ws://<host>/ws/chat/<channel_id>/
```

Após conectar, envie objetos JSON com `tipo` e `conteudo` para publicar
mensagens. O servidor transmite eventos de novos participantes,
reações, pins e moderação para todos os conectados.

## Permissões e papéis

- **Participante** – pode ler e enviar mensagens.
- **Admin** – gerencia metadados e participantes do canal.
- **Moderador** – aprova ou remove mensagens sinalizadas.

## Configuração

- Defina `ASGI_APPLICATION=Hubx.asgi.application` e `REDIS_URL` para
  habilitar o Channels.
- Execute o worker Celery: `celery -A Hubx worker -l info`.
- Variáveis de notificação e demais integrações são lidas de
  `settings` (ver exemplos em `start_server.py`).

## Exportação de histórico

Arquivos JSON possuem uma lista de objetos com `id`, `remetente`,
`tipo`, `conteudo` e `timestamp`. No formato CSV, o cabeçalho segue a
mesma estrutura. Mensagens ocultas por moderação são ignoradas.
