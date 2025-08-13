---
id: REQ-CHAT-001
title: Requisitos Chat Hubx
module: chat
status: Em vigor
version: "1.1.0"
authors: [preencher@hubx.space]
created: "2025-07-25"
updated: "2025-08-13"
owners: [preencher]
reviewers: [preencher]
tags: [backend, api, frontend, segurança, lgpd]
related_docs: []
dependencies: []
---

## 1. Visão Geral

O módulo **Chat** deve oferecer uma experiência de comunicação em tempo real entre usuários em diferentes contextos organizacionais (privado, núcleo, evento e organização). A solução precisa ser modular e escalável, fornecendo segurança, moderação e integração com outros módulos da plataforma.

## 2. Escopo

### Inclui

* Chat privado (1:1) entre dois usuários do mesmo núcleo.
* Chat de núcleo: canal coletivo para membros de um núcleo.
* Chat de evento: canal para participantes de um evento.
* Chat de organização: canal público para associados e administradores.
* Fixação de mensagens e exportação de histórico para administradores.
* Criação de tarefas ou eventos na agenda a partir de mensagens.
* Geração de resumos de chat e cálculo de tópicos em alta.

### Exclui

* Ferramentas de edição de mensagem além do básico (envio, exclusão, edição pelos moderadores).
* Armazenamento offline de histórico de chat fora da plataforma.

## 3. Requisitos Funcionais

**RF-01 — Comunicação em Tempo Real**
- Descrição: Suporte a WebSocket para comunicação em tempo real.
- Critérios de Aceite: Conexão estável e bidirecional via `ws/chat/<channel_id>/`, garantindo latência p95 ≤ 200 ms.
- Rastreabilidade: UC-01; `ws/chat/<channel_id>/`; Model: `chat.ChatMessage`

**RF-02 — Envio de Mensagens Multimídia**
- Descrição: Enviar e receber mensagens de texto, imagem, vídeo e arquivo.
- Critérios de Aceite: Suporta tipos `text`, `image`, `video` e `file` no modelo de mensagens.
- Rastreabilidade: UC-02; `ws/chat/<channel_id>/`; Model: `chat.ChatMessage`

**RF-03 — Validação de Escopo**
- Descrição: Usuário deve pertencer ao contexto (núcleo, evento ou organização) para se conectar ou enviar mensagens.
- Critérios de Aceite: O consumidor WebSocket valida a associação antes de publicar a mensagem.
- Rastreabilidade: UC-01; `ws/chat/<channel_id>/`; Model: `chat.ChatMessage`

**RF-04 — Notificações em Tempo Real**
- Descrição: Notificação de novas mensagens em tempo real para todos os participantes do canal.
- Critérios de Aceite: Notificações são enviadas via `notify_users` sem necessidade de recarregar a página.
- Rastreabilidade: UC-01; `notify_users`; Model: `chat.ChatNotification`

**RF-05 — Permissões de Administrador**
- Descrição: Administradores podem fixar mensagens e exportar histórico.
- Critérios de Aceite: Admin pode fixar mensagens usando `pinned_at` e solicitar exportação de histórico em JSON/CSV.
- Rastreabilidade: UC-03, UC-04; `ws/chat/<channel_id>/`; Model: `chat.ChatMessage`

**RF-06 — Mensagens Encriptadas**
- Descrição: Quando `e2ee_habilitado` estiver ativo no canal, o conteúdo deve ser armazenado em `conteudo_cifrado`.
- Critérios de Aceite: O servidor nunca persiste o texto em claro.
- Rastreabilidade: UC-01; `ws/chat/<channel_id>/`; Model: `chat.ChatMessage`

**RF-07 — Regras de Retenção**
- Descrição: Canais podem definir `retencao_dias` e tarefas assíncronas devem excluir mensagens e anexos mais antigos.
- Critérios de Aceite: Logs de moderação registram exclusões.
- Rastreabilidade: UC-05; `celery:retencao`; Model: `chat.ChatModerationLog`

**RF-08 — Respostas e Threads**
- Descrição: Usuários podem responder a uma mensagem específica criando vínculo `reply_to`.
- Critérios de Aceite: O cliente exibe a mensagem vinculada.
- Rastreabilidade: UC-02; `ws/chat/<channel_id>/`; Model: `chat.ChatMessage`

**RF-09 — Favoritos e Leitura**
- Descrição: Usuários podem marcar mensagens como favoritas e registrar quem leu cada mensagem.
- Critérios de Aceite: Campo `lido_por` atualizado para todos os leitores.
- Rastreabilidade: UC-02; `ws/chat/<channel_id>/`; Model: `chat.ChatFavorite`

**RF-10 — Detecção de Spam**
- Descrição: Integrar detector de spam heurístico que marca mensagens suspeitas e registra log de moderação.
- Critérios de Aceite: Mensagens suspeitas recebem flag e log correspondente.
- Rastreabilidade: UC-01; `/chat/spam`; Model: `chat.ChatModerationLog`

**RF-11 — Anexos e Varredura de Malware**
- Descrição: Armazenar metadados dos anexos e realizar escaneamento para detectar arquivos infectados.
- Critérios de Aceite: Flag `infected` marcada quando vírus detectado.
- Rastreabilidade: UC-02; `celery:scan`; Model: `chat.ChatAttachment`

**RF-12 — Integração com Agenda**
- Descrição: Permitir criar eventos ou tarefas a partir de mensagens, vinculando-os à mensagem original.
- Critérios de Aceite: Item criado no módulo Agenda e log registrado.
- Rastreabilidade: UC-05; `/api/agenda`; Model: `chat.ChatMessage`

**RF-13 — Resumos de Chat**
- Descrição: Gerar resumos diários ou semanais de conversas.
- Critérios de Aceite: Resumo gravado em `ResumoChat`.
- Rastreabilidade: UC-06; `celery:resumo_chat`; Model: `chat.ResumoChat`

**RF-14 — Tópicos em Alta**
- Descrição: Calcular tópicos em alta periodicamente e armazenar as palavras mais frequentes.
- Critérios de Aceite: Dez palavras mais frequentes registradas em `TrendingTopic`.
- Rastreabilidade: UC-07; `celery:trending_topics`; Model: `chat.TrendingTopic`

**RF-15 — Preferências de Usuário**
- Descrição: Usuário configura tema, salva buscas e ativa resumos diários ou semanais.
- Critérios de Aceite: Preferências persistidas em `UserChatPreference`.
- Rastreabilidade: UC-01; `/api/chat/preferences`; Model: `chat.UserChatPreference`

## 4. Requisitos Não Funcionais

### Performance
- Latência p95 das mensagens em tempo real ≤ 200 ms.
- Exportação de histórico inclui metadados e é gerada em ≤ 500 ms.
- Geração de resumos e trending topics concluída em menos de 1 segundo para até 1 000 mensagens.

### Segurança & LGPD
- Conteúdo das mensagens armazenado cifrado quando a encriptação ponta-a-ponta estiver habilitada.
- Política de retenção por canal remove mensagens e anexos antigos automaticamente.
- Logs de moderação registram ações de edição, exclusão, criação de item, retenção e spam para auditabilidade.

### Observabilidade
- Todas as ações de moderação, criação de item, retenção e spam são registradas em `ChatModerationLog`.

### Acessibilidade & i18n
- …

### Resiliência
- …

### Arquitetura & Escala
- Código modular e documentado com cobertura de testes unitários ≥ 90%.
- Modelos herdam de `TimeStampedModel` e implementam `SoftDeleteModel` para exclusão lógica.
- Sistema suporta ao menos 10 000 conexões WebSocket simultâneas sem degradação perceptível de desempenho.

## 5. Casos de Uso

### UC-01 – Comunicação em Tempo Real
1. Usuário acessa a página de chat e estabelece conexão WebSocket.
2. Envia mensagem via `ChatConsumer`.
3. Mensagem é retransmitida a todos os participantes do canal.

### UC-02 – Enviar Mensagem Multimídia
1. Usuário seleciona tipo de mensagem (texto, imagem, vídeo ou arquivo).
2. Sistema valida permissões e publica no canal correto.
3. Todos os participantes recebem a mensagem em tempo real.

### UC-03 – Fixar Mensagem (Admin)
1. Administrador envia comando de fixação em uma mensagem.
2. Sistema marca a mensagem como fixa (`pinned_at`) e notifica o canal.

### UC-04 – Exportar Histórico (Admin)
1. Administrador solicita exportação de histórico de um canal.
2. Sistema gera arquivo JSON/CSV com mensagens, incluindo filtros por datas e tipos.
3. Relatório fica disponível via `RelatorioChatExport`.

### UC-05 – Criar Evento ou Tarefa a partir de Mensagem
1. Usuário (com permissão) seleciona a opção de criar evento ou tarefa a partir de uma mensagem.
2. Informa título, data de início e fim (e outros campos opcionais).
3. Sistema cria o item no módulo Agenda, vincula-o à mensagem e registra log de moderação.

### UC-06 – Gerar Resumo de Chat
1. Uma tarefa agendada executa `gerar_resumo_chat` para um canal e período (diário/semanal).
2. Sistema consolida as mensagens não ocultadas dos últimos dias, gera um resumo e grava no modelo `ResumoChat`.

### UC-07 – Calcular Trending Topics
1. Uma tarefa agendada executa `calcular_trending_topics` para um canal.
2. Sistema varre as mensagens de texto recentes, calcula as palavras mais frequentes excluindo stop-words e grava os dez tópicos mais frequentes em `TrendingTopic`.

## 6. Regras de Negócio
* Usuário deve estar autenticado e pertencer ao contexto (núcleo, evento ou organização) para se conectar ao canal.
* Apenas administradores podem fixar mensagens e exportar histórico.
* Mensagens sinalizadas por três ou mais usuários devem ser automaticamente ocultadas até revisão de um moderador.
* Para criar eventos ou tarefas a partir de mensagens, o usuário deve possuir as permissões correspondentes no módulo Agenda.

## 7. Modelo de Dados
*Nota:* Todos os modelos herdam de `TimeStampedModel` e usam `SoftDeleteModel` quando apropriado.

### chat.ChatChannel
Descrição: Canal de conversa agrupado por contexto.
Campos:
- `id`: UUID
- `contexto_tipo`: enum('privado','nucleo','evento','organizacao')
- `contexto_id`: UUID
- `titulo`: string
- `descricao`: text
- `imagem`: ImageField
- `e2ee_habilitado`: boolean
- `retencao_dias`: integer
- `categoria`: FK → ChatChannelCategory.id

### chat.ChatParticipant
Descrição: Participação de usuário em canal.
Campos:
- `channel`: FK → ChatChannel.id
- `user`: FK → User.id
- `is_admin`: boolean
- `is_owner`: boolean

### chat.ChatMessage
Descrição: Mensagens enviadas nos canais.
Campos:
- `id`: UUID
- `channel`: FK → ChatChannel.id
- `remetente`: FK → User.id
- `tipo`: enum('text','image','video','file')
- `conteudo`: text
- `conteudo_cifrado`: text
- `arquivo`: FileField
- `reply_to`: FK → ChatMessage.id
- `pinned_at`: datetime
- `lido_por`: M2M(User)
- `hidden_at`: datetime
- `is_spam`: boolean

### chat.ChatMessageReaction
Descrição: Reações de emoji em mensagens.
Campos:
- `message`: FK → ChatMessage.id
- `user`: FK → User.id
- `emoji`: string

### chat.ChatMessageFlag
Descrição: Sinalizações de mensagem pelos usuários.
Campos:
- `message`: FK → ChatMessage.id
- `user`: FK → User.id

### chat.ChatFavorite
Descrição: Mensagens favoritas do usuário.
Campos:
- `user`: FK → User.id
- `message`: FK → ChatMessage.id

### chat.ChatNotification
Descrição: Notificações de mensagens.
Campos:
- `usuario`: FK → User.id
- `mensagem`: FK → ChatMessage.id
- `lido`: boolean

### chat.ChatAttachment
Descrição: Metadados de anexos.
Campos:
- `id`: UUID
- `mensagem`: FK → ChatMessage.id
- `arquivo`: FileField
- `mime_type`: string
- `tamanho`: integer
- `thumb_url`: URL
- `preview_ready`: boolean
- `infected`: boolean

### chat.RelatorioChatExport
Descrição: Relatórios de exportação de histórico.
Campos:
- `channel`: FK → ChatChannel.id
- `formato`: string
- `gerado_por`: FK → User.id
- `status`: string
- `arquivo_url`: URL

### chat.ChatModerationLog
Descrição: Logs de ações de moderação.
Campos:
- `message`: FK → ChatMessage.id
- `action`: enum('approve','remove','edit','create_item','retencao','spam')
- `moderator`: FK → User.id
- `previous_content`: text

### chat.TrendingTopic
Descrição: Tópicos em alta nos canais.
Campos:
- `canal`: FK → ChatChannel.id
- `palavra`: string
- `frequencia`: integer
- `periodo_inicio`: datetime
- `periodo_fim`: datetime

### chat.ResumoChat
Descrição: Resumos de conversas por período.
Campos:
- `id`: UUID
- `canal`: FK → ChatChannel.id
- `periodo`: enum('diario','semanal')
- `conteudo`: text
- `gerado_em`: datetime
- `detalhes`: JSON

### chat.UserChatPreference
Descrição: Preferências do usuário para o chat.
Campos:
- `id`: UUID
- `user`: O2O → User.id
- `tema`: enum('claro','escuro')
- `buscas_salvas`: JSON
- `resumo_diario`: boolean
- `resumo_semanal`: boolean

### Modelos Auxiliares
- **ChatChannelCategory** – organiza canais em categorias (`id`, `nome`, `descricao`).

## 8. Critérios de Aceite (Gherkin)

```gherkin
Feature: Envio de mensagens com reações
  Scenario: Usuário reage com emoji a uma mensagem
    Given usuário autenticado participa do canal
    When envia reação 👍 à mensagem
    Then a reação é registrada e contadores de emoji são atualizados para todos

Feature: Criação de tarefa a partir de mensagem
  Scenario: Admin cria uma tarefa de agenda a partir de uma mensagem
    Given mensagem existente no canal
    And admin possui permissão de adicionar tarefa
    When escolhe tipo "tarefa" e preenche título, início e fim
    Then uma nova tarefa é registrada no módulo Agenda e vinculada à mensagem
```

## 9. Dependências e Integrações
* **WebSocket/Channels** – consumo em `chat/consumers.py`.
* **Channels Redis** – camada de broadcast e grupo de canais.
* **Modelos** – `chat.models.ChatChannel`, `chat.models.ChatMessage` e demais entidades listadas acima.
* **Agenda Service** – integração para criar eventos e tarefas a partir de mensagens.
* **Celery** – tarefas assíncronas para retenção, varredura de anexos, geração de resumos, exportação de histórico e trending topics.
* **Spam Detector** – módulo `chat/spam.py` implementa heurísticas para detectar spam.
* **Sentry** – monitoramento de erros.

## Anexos e Referências
…

## Changelog
- 1.1.0 — 2025-08-13 — Normalização do documento

