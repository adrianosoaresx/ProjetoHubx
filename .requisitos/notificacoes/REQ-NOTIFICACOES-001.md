---
id: REQ-NOTIFICACOES-001
title: "Requisitos do M\xF3dulo de Notifica\xE7\xF5es"
module: notificacoes
status: draft
version: 1.0.0
authors: Time de Engenharia Hubx.space
created: 2025-07-28
updated: 2025-07-28
---

## 1. Visão Geral

O módulo **Notificações** centraliza o envio de mensagens transacionais (como cobranças, avisos de inadimplência, confirmações de inscrição) para usuários do Hubx.space.  
Atualmente, cada aplicação envia notificações por conta própria ou registra apenas logs【341912000934825†L9-L21】, o que fragmenta a lógica e dificulta a gestão de preferências e integrações externas.  
Este documento descreve um novo app de notificações que padroniza templates, preferências, envio assíncrono, registro de logs e exposição de métricas.


## 2. Escopo


- **Inclui**:
  - Cadastro de modelos de mensagens com assunto e corpo parametrizáveis.
  - Armazenamento de preferências de notificação por usuário (e‑mail, push, WhatsApp).
  - Envio de notificações de forma assíncrona via Celery, com retentativas automáticas.
  - Registro de logs de envios, incluindo data, canal, status e erro.
  - Integração com provedores externos de envio (APIs de e‑mail, push e WhatsApp), a ser configurado pela equipe de infra.
  - Exposição de métricas Prometheus para contadores de notificações enviadas e falhas【805472933500524†L4-L10】.
- **Exclui**:
  - Interfaces de usuário para configurar preferências (serão tratadas pelo app de contas).
  - Campanhas de marketing ou newsletters; o foco são mensagens transacionais.
  - Armazenamento de mensagens recebidas; este app trata apenas de envio.


## 3. Requisitos Funcionais

- **RF‑01 – Cadastro de Modelos de Notificação**
  - **Descrição**: Administradores devem poder criar e editar modelos de notificação, definindo um código único, assunto, corpo (com placeholders) e canal padrão (e‑mail, push, WhatsApp ou todos).
  - **Prioridade**: Alta.
  - **Critérios de Aceite**: CRUD disponível via interface administrativa; tenta excluir modelo em uso resulta em erro sugerindo desativação.

- **RF‑02 – Preferências de Notificação por Usuário**
  - **Descrição**: Armazenar, para cada usuário, se ele aceita receber notificações via e‑mail, push e WhatsApp. Por padrão, todos os canais estão habilitados.
  - **Prioridade**: Média.
  - **Critérios de Aceite**: O sistema deve consultar essas preferências antes de enviar notificações; se um canal estiver desabilitado, deve registrar falha e não enviar.

- **RF‑03 – Disparo de Notificações**
  - **Descrição**: Expor um serviço interno (`enviar_para_usuario`) que recebe o código do template e um contexto e agenda o envio de mensagens para o usuário nos canais permitidos.
  - **Prioridade**: Alta.
  - **Critérios de Aceite**: Se o template não existir ou estiver inativo, retornar erro; caso contrário, logar a notificação como pendente e disparar task assíncrona.

- **RF‑04 – Envio Assíncrono e Retentativas**
  - **Descrição**: O envio deve ocorrer via Celery, permitindo até 3 tentativas automáticas em caso de falhas temporárias. Cada envio registra sucesso ou falha em `NotificationLog`.
  - **Prioridade**: Alta.
  - **Critérios de Aceite**: Task Celery recebe usuário, template e canal, chama cliente externo e grava o resultado; em caso de falha, repete até 3 vezes.

- **RF‑05 – Registro de Logs de Notificação**
  - **Descrição**: Toda notificação enviada deve gerar registro contendo usuário, template, canal, status (ENVIADA/FALHA), data de envio e descrição do erro (quando houver).
  - **Prioridade**: Alta.
  - **Critérios de Aceite**: Logs devem ser acessíveis via admin, não podem ser editados nem excluídos.

- **RF‑06 – Métricas de Notificação**
  - **Descrição**: Expor contadores Prometheus para número de mensagens enviadas e falhas por canal, além de contagem de templates cadastrados【317521869546451†L29-L42】.
  - **Prioridade**: Média.
  - **Critérios de Aceite**: Endpoint `/metrics` deve conter métricas `notificacoes_enviadas_total`, `notificacoes_falhadas_total` por canal e `templates_total`.

- **RF‑07 – Integração com Outros Módulos**
  - **Descrição**: Permitir que módulos como Financeiro, Agenda, Núcleos etc. chamem `enviar_para_usuario` para notificar seus usuários. Cada módulo deve criar seus próprios templates.
  - **Prioridade**: Alta.
  - **Critérios de Aceite**: Chamadas a partir de outros módulos devem funcionar sem necessidade de conhecer a implementação interna do app de notificações.


## 4. Requisitos Não‑Funcionais

- **RNF‑01 – Desempenho**
  - **Categoria**: Performance.
  - **Descrição**: Agendar o envio deve ocorrer em menos de 300 ms (p95). Processar até 5 000 notificações em lote deve demorar menos de 5 minutos.
  - **Métrica/Meta**: 300 ms para agendamento; 5 min para 5 000 envios.

- **RNF‑02 – Segurança**
  - **Categoria**: Segurança.
  - **Descrição**: Chaves e tokens de provedores externos devem ser lidos de variáveis de ambiente. Apenas serviços internos autorizados podem disparar notificações.
  - **Métrica/Meta**: 0 vazamentos de credenciais.

- **RNF‑03 – Escalabilidade**
  - **Categoria**: Escalabilidade.
  - **Descrição**: Suportar múltiplos workers Celery e filas distribuídas, permitindo que o sistema cresça horizontalmente.
  - **Métrica/Meta**: Processar 10 000 notificações por hora sem degradação perceptível.

- **RNF‑04 – Observabilidade**
  - **Categoria**: Observabilidade.
  - **Descrição**: Registrar logs estruturados de cada envio; expor métricas Prometheus; integrar com Sentry para capturar exceções nas tasks.
  - **Métrica/Meta**: 100 % das tarefas logadas; métricas disponíveis no dashboard.

- **RNF‑05 – Internacionalização**
  - **Categoria**: Usabilidade.
  - **Descrição**: Mensagens de erro e textos padrão devem usar `gettext_lazy` para permitir tradução para outros idiomas.
  - **Métrica/Meta**: 100 % das mensagens extraídas em arquivos `.po`.

- **RNF‑06 – Auditoria**
  - **Categoria**: Conformidade.
  - **Descrição**: Os logs devem permitir rastrear quem enviou, quando e por qual canal, atendendo requisitos da LGPD.
  - **Métrica/Meta**: Logs acessíveis por 5 anos.


- **RNF‑07**: Todos os modelos deste app devem herdar de `TimeStampedModel` para timestamps automáticos (`created` e `modified`), garantindo consistência e evitando campos manuais.
- **RNF‑08**: Quando houver necessidade de exclusão lógica, os modelos devem implementar `SoftDeleteModel` (ou mixin equivalente), evitando remoções físicas e padronizando os campos `deleted` e `deleted_at`.


## 5. Casos de Uso

### UC‑01 – Enviar Notificação Individual
1. Um módulo solicita ao serviço de notificações o envio de uma mensagem para um usuário, informando o código do template e o contexto (ex.: {nome, valor}).
2. O sistema verifica se existe um template ativo com esse código.
3. O sistema aplica o contexto aos placeholders do template.
4. O sistema verifica as preferências do usuário e agenda tarefas para cada canal habilitado.
5. As tarefas Celery enviam a mensagem e atualizam o log como ENVIADA ou FALHA.

### UC‑02 – Enviar Notificação em Massa
1. Um administrador ou módulo interno obtém uma lista de destinatários (ex.: associados inadimplentes).
2. Para cada destinatário, chama `enviar_para_usuario` com o template e contexto apropriados.
3. O módulo de notificações agenda e executa o envio assíncrono de cada mensagem.

### UC‑03 – Gerenciar Templates
1. Um administrador acessa o painel de administração.
2. O administrador cria, edita ou desativa templates definindo código, assunto, corpo e canal padrão.
3. Ao tentar excluir um template em uso, o sistema impede a exclusão e recomenda apenas desativá‑lo.

### UC‑04 – Gerenciar Preferências
1. Um usuário (ou administrador) acessa um painel de configuração de notificações no app de contas.
2. O usuário marca ou desmarca canais (e‑mail, push, WhatsApp).
3. O módulo de notificações lê essas preferências para futuros envios.

### UC‑05 – Auditar Envios
1. Um administrador acessa a listagem de logs no painel de administração.
2. Filtra por usuário, template, canal ou período.
3. Analisa se as mensagens foram enviadas com sucesso ou tiveram falhas.


## 6. Regras de Negócio

- O sistema deve **respeitar as preferências do usuário**: nunca enviar mensagens por canais desativados; se todos os canais estiverem desativados, registrar falha no log.
- Cada template de notificação deve possuir um **código único**, utilizado pelos módulos para referenciar o template.
- Falhas temporárias no envio (ex.: erros 5xx, timeouts) devem ser **re‑tentadas automaticamente** até três vezes com backoff exponencial.
- Os **logs de notificações são imutáveis**: uma vez gravados, não podem ser editados nem excluídos.
- Os registros de preferências e logs devem manter **integridade referencial** com o modelo de usuário (`settings.AUTH_USER_MODEL`); a exclusão de usuários deve ser protegida.


## 7. Modelo de Dados


*Nota:* Todos os modelos herdam de `TimeStampedModel` (campos `created` e `modified`) e utilizam `SoftDeleteModel` para exclusão lógica quando necessário. Assim, campos de timestamp e exclusão lógica não são listados individualmente.

- **NotificationTemplate**
  - `id`: UUID.
  - `codigo`: slug único.
  - `assunto`: string.
  - `corpo`: texto com placeholders.
  - `canal`: enum ('email','push','whatsapp','todos').
  - `ativo`: boolean.
  - ``, ``: datetime.

- **UserNotificationPreference**
  - `id`: UUID.
  - `user`: FK → User.id.
  - `email`: boolean.
  - `push`: boolean.
  - `whatsapp`: boolean.
  - ``, ``: datetime.

- **NotificationLog**
  - `id`: UUID.
  - `user`: FK → User.id.
  - `template`: FK → NotificationTemplate.id.
  - `canal`: enum ('email','push','whatsapp').
  - `status`: enum ('ENVIADA','FALHA').
  - `data_envio`: datetime.
  - `erro`: texto (opcional).
  - ``, ``: datetime.


## 8. Critérios de Aceite (Gherkin)

```gherkin
Feature: Enviar notificações

  Scenario: Enviar notificação de cobrança via e‑mail
    Given existe um template "mensalidade_associacao" ativo
      And um usuário com preferência de e‑mail habilitada
    When o módulo financeiro solicita o envio da notificação com contexto {nome: "Ana", valor: "R$100"}
    Then o sistema agenda o envio assíncrono
      And cria um log com status PENDENTE
      And a mensagem é enviada por e‑mail
      And ao completar o envio o log é marcado como ENVIADA

  Scenario: Usuário desativa WhatsApp
    Given um usuário desativou o canal WhatsApp em suas preferências
      And existe um template com canal padrão "whatsapp"
    When qualquer módulo solicita o envio para este usuário
    Then o sistema registra um log com status FALHA
      And a descrição contém "Canal desabilitado pelo usuário"
      And nenhuma mensagem é enviada

  Scenario: Retentativa automática em falha temporária
    Given o provedor de e‑mail retorna erro 500
      And existe um template configurado para canal "email"
    When a task de envio executa
    Then o sistema tenta enviar até três vezes
      And se todas falharem registra o log como FALHA com descrição do erro
```


## 9. Dependências / Integrações

- **Celery** – utilizado para execução assíncrona das tasks de envio de notificação.
- **Prometheus** – exposição de métricas via endpoint `/metrics` conforme padrão【805472933500524†L4-L10】.
- **Modelo de Usuário** – utiliza `settings.AUTH_USER_MODEL` para relacionar preferências e logs.
- **Serviços de e‑mail/push/WhatsApp** – integração via clientes específicos; hoje são stubs que apenas registram logs【341912000934825†L9-L21】, devendo ser implementados pela equipe de infraestrutura.
- **Módulo Financeiro e demais módulos** – deverão utilizar `enviar_para_usuario` para enviar notificações de cobranças, inadimplência e outras comunicações【768480434653939†L9-L33】.
- **Métricas** – integração com `services/metrics.py` para incrementar contadores de notificações.
