---
id: REQ-CHAT-001
title: Requisitos do App Chat
module: Chat
status: Em vigor
version: '1.1'
authors: []
created: '2025-07-25'
updated: '2025-08-12'
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

### RF‑01 – Comunicação em Tempo Real

* Descrição: Suporte a WebSocket para comunicação em tempo real.
* Prioridade: Alta.
* Critérios de Aceite: Conexão estável e bidirecional via `ws/chat/<channel_id>/`, garantindo latência p95 ≤ 200 ms.

### RF‑02 – Envio de Mensagens Multimídia

* Descrição: Envio e recebimento de mensagens de texto, imagem, vídeo e arquivo.
* Prioridade: Alta.
* Critérios de Aceite: Suporta tipos `text`, `image`, `video` e `file` no modelo de mensagens【928934434084449†L106-L118】.

### RF‑03 – Validação de Escopo

* Descrição: O usuário deve pertencer ao contexto (núcleo, evento ou organização) para se conectar ou enviar mensagens.
* Prioridade: Alta.
* Critérios de Aceite: O consumidor WebSocket valida a associação antes de publicar a mensagem【297096101432642†L31-L63】.

### RF‑04 – Notificações em Tempo Real

* Descrição: Notificação de novas mensagens em tempo real para todos os participantes do canal.
* Prioridade: Média.
* Critérios de Aceite: Notificações são enviadas via `notify_users` sem necessidade de recarregar a página【297096101432642†L111-L129】.

### RF‑05 – Permissões de Administrador

* Descrição: Administradores podem fixar mensagens e exportar histórico.
* Prioridade: Baixa.
* Critérios de Aceite: Admin pode fixar mensagens usando o campo `pinned_at` e solicitar exportação de histórico em JSON/CSV【928934434084449†L126-L127】【163227459204568†L110-L172】.

## 4. Requisitos Não‑Funcionais

### RNF‑01 – Desempenho do WebSocket

* A latência máxima de resposta (p95) das mensagens em tempo real deve ser ≤ 200 ms.

### RNF‑02 – Manutenibilidade

* Código modular e documentado.
* Cobertura de testes unitários ≥ 90 %.

### RNF‑03 – Timestamp Automático

* Todos os modelos deste app devem herdar de `TimeStampedModel` para fornecer campos `created` e `modified` automaticamente【928934434084449†L28-L73】.

### RNF‑04 – Exclusão Lógica

* Quando houver necessidade de exclusão, os modelos devem implementar `SoftDeleteModel` (ou mixin equivalente), evitando remoções físicas e padronizando campos `deleted` e `deleted_at`【928934434084449†L28-L73】.

### RNF‑05 – Escalabilidade de Conexões

* O sistema deve suportar ao menos 10 000 conexões WebSocket simultâneas sem degradação perceptível de desempenho.

### RNF‑06 – Exportação de Histórico

* Históricos exportados devem incluir metadados (remetente, timestamp, tipo) e ser gerados em ≤ 500 ms【163227459204568†L110-L172】.

### RNF‑07 – Segurança de Dados

* Quando a encriptação ponta‑a‑ponta estiver habilitada, o conteúdo das mensagens deve ser armazenado apenas na forma cifrada no campo `conteudo_cifrado`, garantindo que o servidor não tenha acesso ao texto em claro【297096101432642†L91-L126】.

### RNF‑08 – Retenção de Dados

* A política de retenção (`retencao_dias`) deve permitir configuração por canal. Mensagens mais antigas que esse período e seus anexos devem ser removidos automaticamente por tarefas de background【163227459204568†L46-L75】.

### RNF‑09 – Privacidade e Moderation

* Logs de moderação devem ser armazenados para cada ação de edição, exclusão, criação de item, aplicação de retenção ou spam, garantindo auditabilidade【928934434084449†L269-L285】.

## 5. Casos de Uso

### UC‑01 – Comunicação em Tempo Real

1. Usuário acessa a página de chat e estabelece conexão WebSocket.
2. Envia mensagem via `ChatConsumer`.
3. Mensagem é retransmitida a todos os participantes do canal.

### UC‑02 – Enviar Mensagem Multimídia

1. Usuário seleciona tipo de mensagem (texto, imagem, vídeo ou arquivo).
2. Sistema valida permissões e publica no canal correto.
3. Todos os participantes recebem a mensagem em tempo real.

### UC‑03 – Fixar Mensagem (Admin)

1. Administrador envia comando de fixação em uma mensagem.
2. Sistema marca a mensagem como fixa (`pinned_at`) e notifica o canal.

### UC‑04 – Exportar Histórico (Admin)

1. Administrador solicita exportação de histórico de um canal.
2. Sistema gera arquivo JSON/CSV com mensagens, incluindo filtros por datas e tipos.
3. Relatório fica disponível via `RelatorioChatExport`.

### UC‑05 – Criar Evento ou Tarefa a partir de Mensagem

1. Usuário (com permissão) seleciona a opção de criar evento ou tarefa a partir de uma mensagem.
2. Informa título, data de início e fim (e outros campos opcionais).
3. Sistema cria o item no módulo Agenda, vincula‑o à mensagem e registra log de moderação【59335525396973†L167-L235】.

### UC‑06 – Gerar Resumo de Chat

1. Uma tarefa agendada executa `gerar_resumo_chat` para um canal e período (diário/semanal).
2. Sistema consolida as mensagens não ocultadas dos últimos dias, gera um resumo e grava no modelo `ResumoChat`【163227459204568†L89-L107】.

### UC‑07 – Calcular Trending Topics

1. Uma tarefa agendada executa `calcular_trending_topics` para um canal.
2. Sistema varre as mensagens de texto recentes, calcula as palavras mais frequentes excluindo stop‑words e grava os dez tópicos mais frequentes em `TrendingTopic`【163227459204568†L190-L241】.

## 6. Regras de Negócio

* Usuário deve estar autenticado e pertencer ao contexto (núcleo, evento ou organização) para se conectar ao canal【297096101432642†L31-L63】.
* Apenas administradores podem fixar mensagens e exportar histórico.
* Mensagens sinalizadas por três ou mais usuários devem ser automaticamente ocultadas até revisão de um moderador【59335525396973†L149-L165】.
* Para criar eventos ou tarefas a partir de mensagens, o usuário deve possuir as permissões correspondentes no módulo Agenda【59335525396973†L167-L235】.

## 7. Modelo de Dados

*Nota:* Todos os modelos herdam de `TimeStampedModel` e usam `SoftDeleteModel` quando apropriado. Campos de timestamp e exclusão lógica não são listados individualmente.

### Entidades Principais

- ** ChatChannel **

 -id: UUID
 -contexto_tipo: enum('privado','nucleo','evento','organizacao')
 -contexto_id: UUID
 -titulo: string
 -descricao: text
 -imagem: ImageField
 -e2ee_habilitado: boolean
 -retencao_dias: integer
 -categoria: FK → ChatChannelCategory.id
 -ChatParticipant
 -channel: FK → ChatChannel.id
 -user: FK → User.id
 -is_admin: boolean
 -is_owner: boolean

-** ChatMessage **
 -id: UUID
 -channel: FK → ChatChannel.id
 -remetente: FK → User.id
 -tipo: enum('text','image','video','file')
 -conteudo: text
 -conteudo_cifrado: text
 -arquivo: FileField
 -reply_to: FK → ChatMessage.id
 -pinned_at: datetime
 -lido_por: M2M(User)
 -hidden_at: datetime
 -is_spam: boolean
 -ChatMessageReaction
 -message: FK → ChatMessage.id
 -user: FK → User.id
 -emoji: string
 -ChatMessageFlag
 -message: FK → ChatMessage.id
 -user: FK → User.id
 -ChatFavorite
 -user: FK → User.id
 -message: FK → ChatMessage.id

-** ChatNotification ** 
 -usuario: FK → User.id
 -mensagem: FK → ChatMessage.id
 -lido: boolean

-** ChatAttachment **
 -id: UUID
 -mensagem: FK → ChatMessage.id
 -arquivo: FileField
 -mime_type: string
 -tamanho: integer
 -thumb_url: URL
 -preview_ready: boolean
 -infected: boolean
 -RelatorioChatExport
 -channel: FK → ChatChannel.id
 -formato: string
 -gerado_por: FK → User.id
 -status: string
 -arquivo_url: URL

-** ChatModerationLog **
 -message: FK → ChatMessage.id
 -action: enum('approve','remove','edit','create_item','retencao','spam')
 -moderator: FK → User.id
 -previous_content: text

- ** TrendingTopic **
 -canal: FK → ChatChannel.id
 -palavra: string
 -frequencia: integer
 -periodo_inicio: datetime
 -periodo_fim: datetime
 -ResumoChat
 -id: UUID
 -canal: FK → ChatChannel.id
 -periodo: enum('diario','semanal')
 -conteudo: text
 -gerado_em: datetime
 -detalhes: JSON

-** UserChatPreference **
 -id: UUID
 -user: O2O → User.id
 -tema: enum('claro','escuro')
 -buscas_salvas: JSON
 -resumo_diario: boolean
 -resumo_semanal: boolean

### Modelos Auxiliares

* **ChatChannelCategory** – organiza canais em categorias (campos `id`, `nome`, `descricao`)【928934434084449†L13-L27】.

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

## 9. Dependências / Integrações

* **WebSocket/Channels** – consumo em `chat/consumers.py`.
* **Channels Redis** – camada de broadcast e grupo de canais.
* **Modelos** – `chat.models.ChatChannel`, `chat.models.ChatMessage` e demais entidades listadas acima.
* **Agenda Service** – integração para criar eventos e tarefas a partir de mensagens.
* **Celery** – tarefas assíncronas para retenção, varredura de anexos, geração de resumos, exportação de histórico e trending topics【163227459204568†L46-L189】.
* **Spam Detector** – módulo `chat/spam.py` implementa heurísticas para detectar spam【684477192136048†L15-L40】.
* **Sentry** – monitoramento de erros.

## 10. Requisitos Adicionais / Melhorias (v1.1)

### Requisitos Funcionais Adicionais

* **RF‑10** – **Mensagens Encriptadas**: quando `e2ee_habilitado` estiver ativo no canal, o conteúdo deve ser armazenado no campo `conteudo_cifrado`. O servidor nunca deve persistir o texto em claro【297096101432642†L91-L126】.
* **RF‑11** – **Regras de Retenção**: canais podem definir `retencao_dias`; tarefas assíncronas devem excluir mensagens e anexos mais antigos que esse limite e registrar logs de moderação【163227459204568†L46-L75】.
* **RF‑12** – **Repostas e Threads**: usuários podem responder a uma mensagem específica, criando um vínculo (`reply_to`) que deve ser exibido no cliente【928934434084449†L119-L125】.
* **RF‑13** – **Favoritos e Leitura**: usuários podem marcar mensagens como favoritas; o sistema deve registrar quem leu cada mensagem no campo `lido_por`【928934434084449†L133-L134】.
* **RF‑14** – **Detecção de Spam**: integrar detector de spam heurístico que marca mensagens suspeitas e registra log de moderação【684477192136048†L15-L40】【59335525396973†L112-L130】.
* **RF‑15** – **Anexos e Varredura de Malware**: armazenar metadados de anexos em `ChatAttachment` e realizar escaneamento para detectar arquivos infectados【928934434084449†L232-L250】【163227459204568†L76-L87】.
* **RF‑16** – **Integração com Agenda**: permitir criar eventos ou tarefas a partir de mensagens, vinculando‐os à mensagem original e registrando logs【59335525396973†L167-L235】.
* **RF‑17** – **Resumos de Chat**: gerar resumos diários ou semanais de conversas, registrando o conteúdo e estatísticas em `ResumoChat`【163227459204568†L89-L107】.
* **RF‑18** – **Tópicos em Alta**: calcular tópicos em alta periodicamente, armazenando as 10 palavras mais frequentes em `TrendingTopic`【163227459204568†L190-L241】.
* **RF‑19** – **Preferências de Usuário**: permitir que o usuário configure tema (claro ou escuro), salve buscas e ative resumos diários ou semanais nas suas preferências (`UserChatPreference`)【928934434084449†L322-L339】.

### Requisitos Não‑Funcionais Adicionais

* **RNF‑10** – **Segurança de Encriptação**: a implementação de encriptação ponta‑a‑ponta deve garantir que apenas clientes autorizados possam descriptografar mensagens.
* **RNF‑11** – **Auditoria Completa**: todas as ações de moderação, criação de item, retenção e spam devem ser registradas em `ChatModerationLog`, assegurando rastreabilidade【928934434084449†L269-L285】.
* **RNF‑12** – **Desempenho de Tarefas**: a geração de resumos e trending topics deve ser concluída em tempo aceitável (ex.: menos de 1 segundo para resumos de até 1 000 mensagens), permitindo execução periódica sem impactar o desempenho da plataforma.
