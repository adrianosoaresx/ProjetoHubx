# Chat API

Módulo responsável pela comunicação em tempo real da plataforma. Os
recursos são expostos via REST e WebSocket e dependem de Redis,
Celery e Django Channels.

## Entidades

Todos os modelos utilizam `TimeStampedModel`, expondo os campos
`created_at` e `updated_at`. Quando necessário, a exclusão lógica é feita
com `SoftDeleteModel`, que adiciona `deleted` e `deleted_at`. Registros
removidos podem ser acessados via `Model.all_objects` e restaurados
definindo `deleted=False` e `deleted_at=None`.

- **ChatChannel** – canal de conversa associado a um contexto (núcleo,
  evento, organização ou privado). Possui exclusão lógica.
- **ChatParticipant** – relação de usuários com o canal, indicando
  proprietários e administradores.
- **ChatMessage** – mensagens enviadas no canal, com suporte a texto,
  arquivos e reações. Possui exclusão lógica e campos de moderação
  como `hidden_at` e `pinned_at`.
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

- `desde=<ISO8601>` – mensagens a partir de uma data/hora.
- `ate=<ISO8601>` – mensagens até uma data/hora.

### Exportar histórico

```http
GET /api/chat/channels/<id>/export/?formato=csv
```

A chamada cria um `RelatorioChatExport` e, após processamento assíncrono,
disponibiliza um arquivo JSON ou CSV com as mensagens visíveis.

### Configurar política de retenção

```http
PATCH /api/chat/channels/<id>/config-retention/
Content-Type: application/json

{"retencao_dias": 30}
```

Define ou remove (`null`) o limite de dias para exclusão automática de mensagens do canal. Somente administradores podem alterar a configuração.

### Limpeza automática de anexos

Ao excluir mensagens ou anexos, os arquivos correspondentes são removidos do
storage automaticamente por um sinal `post_delete` do modelo
`ChatAttachment`. Isso vale também para mensagens eliminadas pela política de
retenção, evitando a criação de arquivos órfãos.

## Criptografia de ponta a ponta (E2EE)

Quando um canal tem `e2ee_habilitado` ativado, o cliente deve cifrar o conteúdo
das mensagens antes do envio. A implementação utiliza a Web Crypto API com
`AES-GCM`, combinando um vetor de inicialização aleatório com o texto cifrado e
codificando o resultado em Base64. O servidor armazena somente os campos
`conteudo_cifrado`, `alg` (sempre `AES-GCM`) e `key_version`.

Exemplo de payload cifrado:

```json
{
  "tipo": "text",
  "conteudo_cifrado": "BASE64(iv+ciphertext)",
  "alg": "AES-GCM",
  "key_version": "1"
}
```

## WebSocket

Conexão:

```
ws://<host>/ws/chat/<channel_id>/
```

Após conectar, envie objetos JSON com `tipo` e `conteudo` para publicar
mensagens. O servidor transmite eventos de novos participantes,
reações, pins e moderação para todos os conectados.

O script `static/chat/js/chat_socket.js` utiliza `window.location.host` para
montar a URL padrão de conexão. Em cenários com proxy reverso, é possível
sobrescrever o host definindo a variável global `CHAT_WS_URL` ou atribuindo um
valor ao atributo `data-ws-url` no container do chat.

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

### Limiar de spam

O detector de spam utiliza parâmetros configuráveis em `settings`:

```python
CHAT_SPAM_MESSAGES_PER_MINUTE = 20
CHAT_SPAM_REPEAT_LIMIT = 3
CHAT_SPAM_LINK_LIMIT = 3
```

Ajuste os valores conforme a necessidade do ambiente. A contagem de
mensagens por usuário é mantida em cache por até um minuto. O limite de
mensagens no WebSocket também utiliza o cache (ex.: Redis) para registrar
os envios de cada usuário por canal, expurgando os dados após o período da
janela configurado.

### Limites de upload

O endpoint `POST /api/chat/upload/` aceita apenas arquivos de até 20 MB e
limitados aos tipos MIME `image/*`, `video/*`, `audio/*`, `application/pdf`
e `text/plain`. Os valores podem ser configurados via `CHAT_ALLOWED_MIME_TYPES`
e `CHAT_UPLOAD_MAX_SIZE` em `settings`.

## Exportação de histórico

Arquivos JSON possuem uma lista de objetos com `id`, `remetente`,
`tipo`, `conteudo` e `created_at`. No formato CSV, o cabeçalho segue a
mesma estrutura. Mensagens ocultas por moderação são ignoradas.
Mensagens removidas pela política de retenção não são incluídas nas exportações.

## Janela de chat flutuante

O módulo expõe uma interface de conversa em janela flutuante.
Para utilizá‑la, inclua o container com `id="chat-float-container"`
e um link com `id="chat-link"` na página. O script `static/js/chat_modal.js`
carrega a lista de usuários e as conversas via requisições assíncronas.
Usuários não autenticados são redirecionados para a página de login.
## Busca e histórico

- O template `conversation_detail.html` fornece um formulário com campo de busca, filtros de data e tipo de mensagem. Os resultados são carregados via `fetch` no endpoint `/api/chat/channels/<id>/messages/search/` e exibidos abaixo do campo em lista paginada.
- O script `static/chat/js/chat_socket.js` implementa scroll infinito consultando `/messages/history?before=<id>` para carregar mensagens anteriores. O endpoint retorna lotes de 20 mensagens ordenadas decrescentemente e informa se há mais dados.

## Acessibilidade

Cada mensagem renderizada em `partials/message.html` inclui um botão de reação com menu acessível via teclado e atributos ARIA. As reações existentes ficam dentro de `<ul class="reactions">`, permitindo que o JavaScript atualize contagens em tempo real.
