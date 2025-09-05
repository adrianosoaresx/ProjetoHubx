---
id: REQ-NOTIFICACOES-001
title: Requisitos notificacoes Hubx
module: notificacoes
status: Rascunho
version: "1.0.0"
authors: [preencher@hubx.space]
created: "2025-07-28"
updated: "2025-08-13"
owners: [preencher]
reviewers: [preencher]
tags: [backend, api, frontend, segurança, lgpd]
related_docs: []
dependencies: []
---

## 1. Visão Geral

O módulo **Notificações** centraliza o envio de mensagens transacionais (como cobranças, avisos de inadimplência e confirmações de inscrição) para usuários do Hubx.space. Atualmente, cada aplicação envia notificações por conta própria ou registra apenas logs, o que fragmenta a lógica e dificulta a gestão de preferências e integrações externas. Este documento descreve um app que padroniza templates, preferências, envio assíncrono, registro de logs e exposição de métricas.

## 2. Escopo

- Inclui:
  - Cadastro de modelos de mensagens com assunto e corpo parametrizáveis.
  - Armazenamento de preferências de notificação por usuário (e‑mail, push, WhatsApp).
  - Envio de notificações de forma assíncrona via Celery, com retentativas automáticas.
  - Registro de logs de envios, incluindo data, canal, status e erro.
  - Integração com provedores externos de envio (APIs de e‑mail, push e WhatsApp).
  - Exposição de métricas Prometheus para contadores de notificações enviadas e falhas.
- Exclui:
  - Interfaces de usuário para configurar preferências (tratadas pelo app de contas).
  - Campanhas de marketing ou newsletters; o foco são mensagens transacionais.
  - Armazenamento de mensagens recebidas; este app trata apenas de envio.

## 3. Requisitos Funcionais

**RF-01 — Cadastro de Modelos de Notificação**
- Descrição: Administradores podem criar e editar modelos de notificação com código único, assunto, corpo com placeholders e canal padrão (e‑mail, push, WhatsApp ou todos).
- Critérios de Aceite: CRUD disponível via interface administrativa; tentativa de excluir modelo em uso retorna erro sugerindo desativação.
- Rastreabilidade: UC-03; `/admin/notificacoes/templates/`; Model: Notificacoes.NotificationTemplate

**RF-02 — Preferências de Notificação por Usuário**
- Descrição: Armazenar para cada usuário se aceita notificações via e‑mail, push e WhatsApp; por padrão todos os canais habilitados.
- Critérios de Aceite: Sistema consulta preferências antes de enviar; canal desabilitado gera falha registrada.
- Rastreabilidade: UC-04; Model: Notificacoes.UserNotificationPreference

**RF-03 — Disparo de Notificações**
- Descrição: Expor serviço interno `enviar_para_usuario` que recebe código de template e contexto e agenda envio nos canais permitidos.
- Critérios de Aceite: Template inexistente ou inativo retorna erro; envio gera log pendente e dispara task assíncrona.
- Rastreabilidade: UC-01; `service.enviar_para_usuario`; Model: Notificacoes.NotificationLog

**RF-04 — Envio Assíncrono e Retentativas**
- Descrição: Envio ocorre via Celery com até três tentativas automáticas em caso de falhas temporárias.
- Critérios de Aceite: Task grava sucesso ou falha em `NotificationLog`; em falha repete até três vezes.
- Rastreabilidade: UC-01; Celery task; Model: Notificacoes.NotificationLog

**RF-05 — Registro de Logs de Notificação**
- Descrição: Toda notificação gera registro com usuário, template, canal, status, data de envio e erro.
- Critérios de Aceite: Logs acessíveis via admin e não podem ser editados ou excluídos.
- Rastreabilidade: UC-05; `/admin/notificacoes/logs/`; Model: Notificacoes.NotificationLog

**RF-06 — Métricas de Notificação**
- Descrição: Expor contadores Prometheus para mensagens enviadas e falhas por canal e contagem de templates cadastrados.
- Critérios de Aceite: Endpoint `/metrics` contém métricas `notificacoes_enviadas_total`, `notificacoes_falhadas_total` por canal e `templates_total`.
- Rastreabilidade: `/metrics`; services.metrics; Model: Notificacoes.NotificationTemplate

**RF-07 — Integração com Outros Módulos**
- Descrição: Permitir que módulos como Financeiro, Eventos e Núcleos chamem `enviar_para_usuario` para notificar seus usuários.
- Critérios de Aceite: Chamadas funcionam sem conhecimento da implementação interna do app.
- Rastreabilidade: UC-01; `service.enviar_para_usuario`; Model: Notificacoes.NotificationTemplate

**RF-08 — Entrega em Tempo Real (WebSocket)**
- Descrição: Publicar eventos de nova notificação no grupo do usuário via `ws/notificacoes/`.
- Critérios de Aceite: Usuário conectado recebe evento `notification_message` ao gerar nova notificação.
- Rastreabilidade: UC-01; `ws/notificacoes/`; Model: Notificacoes.NotificationLog

**RF-09 — Marcar Notificação como LIDA**
- Descrição: Endpoint `PATCH /api/notificacoes/logs/{id}` altera status para LIDA registrando `data_leitura`.
- Critérios de Aceite: Atualização permitida apenas para logs do próprio usuário; campos de leitura preenchidos.
- Rastreabilidade: UC-05; `/api/notificacoes/logs/{id}`; Model: Notificacoes.NotificationLog

**RF-10 — PushSubscription (Web Push)**
- Descrição: CRUD autenticado de inscrições de Web Push, removendo registros inválidos (404/410).
- Critérios de Aceite: Inscrições associadas ao usuário; falha de entrega remove inscrição automaticamente.
- Rastreabilidade: `/api/notificacoes/push/subscriptions/`; Model: Notificacoes.PushSubscription

**RF-11 — Resumos Diário/Semanal (Digest)**
- Descrição: Job agrega pendências por canal conforme frequência configurada e registra `HistoricoNotificacao`.
- Critérios de Aceite: Frequências `diaria` e `semanal` respeitadas; logs consolidados enviados conforme preferências.
- Rastreabilidade: UC-02; Celery job; Model: Notificacoes.HistoricoNotificacao

**RF-12 — Permissão de Disparo por Endpoint**
- Descrição: `POST /api/notificacoes/enviar/` exige permissão `notificacoes.can_send_notifications`.
- Critérios de Aceite: Requisições sem permissão retornam 403; com permissão seguem fluxo normal.
- Rastreabilidade: UC-01; `/api/notificacoes/enviar/`; Model: Notificacoes.NotificationLog

## 4. Requisitos Não Funcionais

### Performance
- **RNF-01 — Desempenho**: Agendar envio em menos de 300 ms (p95) e processar 5 000 notificações em lote em menos de 5 minutos.
- **RNF-02 — Latência In-App**: Eventos WebSocket p95 ≤200 ms.

### Segurança & LGPD
- **RNF-03 — Segurança**: Chaves e tokens de provedores externos em variáveis de ambiente; apenas serviços autorizados podem disparar notificações.
- **RNF-04 — Auditoria**: Logs devem permitir rastrear quem enviou, quando e por qual canal.
- **RNF-05 — Retenção de Logs**: Logs imutáveis com retenção mínima de 5 anos e acesso read-only no admin.

### Observabilidade
- **RNF-06 — Observabilidade**: Registrar logs estruturados de cada envio, expor métricas Prometheus e integrar com Sentry.
- **RNF-07 — Métrica de Duração**: Histogram Prometheus `notificacao_task_duration_seconds`.

### Acessibilidade & i18n
- **RNF-08 — Internacionalização**: Mensagens de erro e textos padrão devem usar `gettext_lazy` para permitir tradução.

### Resiliência
- **RNF-09 — Validação de Ambiente**: Falhar no start se variáveis críticas não estiverem definidas.

### Arquitetura & Escala
- **RNF-10 — Escalabilidade**: Suportar múltiplos workers Celery e filas distribuídas.
- **RNF-11 — TimeStampedModel**: Todos os modelos herdarão de `TimeStampedModel` para timestamps automáticos.
- **RNF-12 — SoftDeleteModel**: Quando necessário, modelos devem implementar `SoftDeleteModel` para exclusão lógica.

## 5. Casos de Uso

### UC-01 – Enviar Notificação Individual
1. Um módulo solicita ao serviço de notificações o envio de uma mensagem para um usuário, informando o código do template e o contexto.
2. O sistema verifica se existe um template ativo com esse código.
3. O sistema aplica o contexto aos placeholders do template.
4. O sistema verifica as preferências do usuário e agenda tarefas para cada canal habilitado.
5. As tarefas Celery enviam a mensagem e atualizam o log como ENVIADA ou FALHA.

### UC-02 – Enviar Notificação em Massa
1. Um administrador ou módulo interno obtém uma lista de destinatários.
2. Para cada destinatário, chama `enviar_para_usuario` com o template e contexto apropriados.
3. O módulo de notificações agenda e executa o envio assíncrono de cada mensagem.

### UC-03 – Gerenciar Templates
1. Um administrador acessa o painel de administração.
2. O administrador cria, edita ou desativa templates definindo código, assunto, corpo e canal padrão.
3. Ao tentar excluir um template em uso, o sistema impede a exclusão e recomenda apenas desativá-lo.

### UC-04 – Gerenciar Preferências
1. Um usuário ou administrador acessa um painel de configuração de notificações no app de contas.
2. O usuário marca ou desmarca canais (e‑mail, push, WhatsApp).
3. O módulo de notificações lê essas preferências para futuros envios.

### UC-05 – Auditar Envios
1. Um administrador acessa a listagem de logs no painel de administração.
2. Filtra por usuário, template, canal ou período.
3. Analisa se as mensagens foram enviadas com sucesso ou tiveram falhas.

## 6. Regras de Negócio
- O sistema deve respeitar as preferências do usuário: nunca enviar mensagens por canais desativados; se todos os canais estiverem desativados, registrar falha no log.
- Cada template de notificação deve possuir um código único, utilizado pelos módulos para referenciar o template.
- Falhas temporárias no envio devem ser re‑tentadas automaticamente até três vezes com backoff exponencial.
- Os logs de notificações são imutáveis: uma vez gravados, não podem ser editados nem excluídos.
- Os registros de preferências e logs devem manter integridade referencial com o modelo de usuário; a exclusão de usuários deve ser protegida.

## 7. Modelo de Dados

Todos os modelos herdam de `TimeStampedModel` (campos `created` e `modified`) e utilizam `SoftDeleteModel` para exclusão lógica quando necessário.

### Notificacoes.NotificationTemplate
Descrição: Modelo parametrizável de mensagem.
Campos:
- `id`: UUID
- `codigo`: slug único — índice: unique
- `assunto`: string
- `corpo`: texto com placeholders
- `canal`: enum('email','push','whatsapp','todos')
- `ativo`: boolean
Constraints adicionais:
- `codigo` único

### Notificacoes.UserNotificationPreference
Descrição: Preferências de canais por usuário.
Campos:
- `id`: UUID
- `user`: FK → User.id
- `email`: boolean
- `push`: boolean
- `whatsapp`: boolean

### Notificacoes.NotificationLog
Descrição: Registro de envios e resultados.
Campos:
- `id`: UUID
- `user`: FK → User.id
- `template`: FK → Notificacoes.NotificationTemplate.id
- `canal`: enum('email','push','whatsapp')
- `status`: enum('ENVIADA','FALHA','LIDA')
- `data_envio`: datetime
- `erro`: texto opcional
- `data_leitura`: datetime opcional

### Notificacoes.PushSubscription
Descrição: Inscrição de Web Push do usuário.
Campos:
- `id`: UUID
- `user`: FK → User.id
- `endpoint`: string
- `chave_p256dh`: string
- `chave_auth`: string
- `ativo`: boolean

### Notificacoes.HistoricoNotificacao
Descrição: Armazena resumos diários ou semanais de notificações.
Campos:
- `id`: UUID
- `user`: FK → User.id
- `canal`: enum('email','push','whatsapp','in_app')
- `frequencia`: enum('diaria','semanal')
- `data_referencia`: date
- `conteudo`: texto

## 8. Critérios de Aceite (Gherkin)

```gherkin
Feature: Enviar notificações
  Scenario: Enviar notificação de cobrança via e-mail
    Given existe um template "mensalidade_associacao" ativo
      And um usuário com preferência de e-mail habilitada
    When o módulo financeiro solicita o envio da notificação com contexto {nome: "Ana", valor: "R$100"}
    Then o sistema agenda o envio assíncrono
      And cria um log com status PENDENTE
      And a mensagem é enviada por e-mail
      And ao completar o envio o log é marcado como ENVIADA

  Scenario: Usuário desativa WhatsApp
    Given um usuário desativou o canal WhatsApp em suas preferências
      And existe um template com canal padrão "whatsapp"
    When qualquer módulo solicita o envio para este usuário
    Then o sistema registra um log com status FALHA
      And a descrição contém "Canal desabilitado pelo usuário"
      And nenhuma mensagem é enviada

  Scenario: Retentativa automática em falha temporária
    Given o provedor de e-mail retorna erro 500
      And existe um template configurado para canal "email"
    When a task de envio executa
    Then o sistema tenta enviar até três vezes
      And se todas falharem registra o log como FALHA com descrição do erro

Feature: Notificações in-app em tempo real
  Scenario: Usuário recebe evento via WebSocket
    Given usuário autenticado com conexão em ws/notificacoes/
    When sistema dispara notificação elegível para in-app
    Then cliente recebe evento "notification_message" com payload JSON em até 200 ms

Feature: Marcar notificação como LIDA
  Scenario: API atualiza status de leitura
    Given existe NotificationLog com status ENVIADA
    When cliente envia PATCH /api/notificacoes/logs/{id} com {"status":"LIDA"}
    Then status do log passa a LIDA
      And "data_leitura" é preenchida
```

## 9. Dependências e Integrações
- Celery — utilizado para execução assíncrona das tasks de envio de notificação.
- Prometheus — exposição de métricas via endpoint `/metrics`.
- Modelo de Usuário — utiliza `settings.AUTH_USER_MODEL` para relacionar preferências e logs.
- Serviços de e-mail/push/WhatsApp — integração via clientes específicos; hoje são stubs que registram logs, devendo ser implementados pela equipe de infraestrutura.
- Módulo Financeiro e demais módulos — utilizam `enviar_para_usuario` para notificações de cobranças, inadimplência e outras comunicações.
- Métricas — integração com `services/metrics.py` para incrementar contadores de notificações.
- Variáveis de ambiente — `NOTIFICATIONS_EMAIL_API_URL`, `NOTIFICATIONS_EMAIL_API_KEY`, `NOTIFICATIONS_WHATSAPP_API_URL`, `NOTIFICATIONS_WHATSAPP_API_KEY`, `ONESIGNAL_APP_ID`, `ONESIGNAL_API_KEY`, `VAPID_PRIVATE_KEY`, `VAPID_CLAIM_SUB`, `DEFAULT_FROM_EMAIL`.

## Anexos e Referências
...

## Changelog
- 1.0.0 — 2025-08-13 — Normalização estrutural.

