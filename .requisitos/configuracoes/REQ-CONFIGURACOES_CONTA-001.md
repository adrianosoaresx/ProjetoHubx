---
id: REQ-CONFIGURACOES_CONTA-001
title: Requisitos Configuracoes Conta Hubx
module: configuracoes
status: Em vigor
version: "1.1.0"
authors: [preencher@hubx.space]
created: "2025-07-25"
updated: "2025-08-13"
owners: [preencher]
reviewers: [preencher]
tags: [backend]
related_docs: []
dependencies: []
---

## 1. Visão Geral

O App de Configurações de Conta (Configuracoes_Conta) permite que cada usuário personalize suas preferências de notificação, aparência e idioma de forma centralizada e persistente. A versão 1.1 estende o escopo original adicionando suporte a notificações push, escolha de horários e dia da semana para resumos, configurações contextuais por escopo (organização, núcleo ou evento) e auditoria de alterações de preferências. O aplicativo utiliza cache para melhorar o tempo de acesso às preferências e fornece API REST para consulta e atualização.

## 2. Escopo

### Inclui

* Gerenciamento de preferências de notificação por e‑mail, WhatsApp e push.
* Definição de frequência (imediata, diária, semanal) para cada canal.
* Definição de idioma da interface (português, inglês ou espanhol).
* Alternância de tema (claro, escuro ou automático).
* Configuração do horário e do dia da semana para envio de resumos agregados.
* Visualização, edição e teste das configurações pessoais via interface e API.
* Criação de configurações de conta no momento do cadastro de usuário.
* Registro de alterações em log para fins de auditoria.
* Possibilidade de criar configurações específicas para escopos (organização, núcleo, evento) que sobrepõem as preferências globais.

### Exclui

* Cadastro e autenticação (delegados ao App Accounts).
* Configurações coletivas de organização ou núcleo (delegadas a módulos específicos).
* Gerenciamento de canais de notificação externos (Twilio, etc.) além das integrações definidas para envio de resumos.

## 3. Requisitos Funcionais

- **RF-01 — Ativar/Desativar Notificações por E-mail**
  - Descrição: O usuário pode habilitar ou desabilitar o recebimento de notificações por e-mail.
  - Critérios de Aceite: Checkbox salva e reflete estado atual no banco.
  - Rastreabilidade: UC-01; Model: Configuracoes.ConfiguracaoConta

- **RF-02 — Ativar/Desativar Notificações por WhatsApp**
  - Descrição: O usuário pode habilitar ou desabilitar o recebimento de notificações via WhatsApp.
  - Critérios de Aceite: Estado persistido em `receber_notificacoes_whatsapp`.
  - Rastreabilidade: UC-01; Model: Configuracoes.ConfiguracaoConta

- **RF-03 — Ativar/Desativar Notificações Push**
  - Descrição: O usuário pode habilitar ou desabilitar o recebimento de notificações push.
  - Critérios de Aceite: Estado persistido em `receber_notificacoes_push`.
  - Rastreabilidade: UC-01; Model: Configuracoes.ConfiguracaoConta

- **RF-04 — Configurar Frequência de Notificações**
  - Descrição: O usuário pode escolher a frequência das notificações (imediata, diária ou semanal) para cada canal.
  - Critérios de Aceite: Campos `frequencia_notificacoes_email`, `frequencia_notificacoes_whatsapp` e `frequencia_notificacoes_push` armazenam o valor selecionado.
  - Rastreabilidade: UC-01; Model: Configuracoes.ConfiguracaoConta

- **RF-05 — Escolher Idioma da Interface**
  - Descrição: Permitir que o usuário selecione o idioma da interface (pt-BR, en-US ou es-ES).
  - Critérios de Aceite: Campo `idioma` salva opção escolhida.
  - Rastreabilidade: UC-02; Model: Configuracoes.ConfiguracaoConta

- **RF-06 — Alternar Tema da Interface**
  - Descrição: O usuário pode alternar o tema entre claro, escuro e automático.
  - Critérios de Aceite: Campo `tema` salva a escolha.
  - Rastreabilidade: UC-02; Model: Configuracoes.ConfiguracaoConta

- **RF-07 — Configurar Horários e Dia da Semana**
  - Descrição: O usuário define horário para notificações diárias e horário e dia da semana para notificações semanais.
  - Critérios de Aceite: Campos persistidos e validados; hora e dia obrigatórios quando frequência diária ou semanal está ativa.
  - Rastreabilidade: UC-01; Model: Configuracoes.ConfiguracaoConta

- **RF-08 — Configuração Automática no Cadastro**
  - Descrição: Ao cadastrar um usuário, uma instância de `ConfiguracaoConta` é criada automaticamente.
  - Critérios de Aceite: Após cadastro, existe instância de `ConfiguracaoConta` associada ao usuário.
  - Rastreabilidade: UC-01; Model: Configuracoes.ConfiguracaoConta

- **RF-09 — Configurações Contextuais por Escopo**
  - Descrição: O usuário pode criar configurações específicas para um escopo (`organizacao`, `nucleo` ou `evento`) que sobrepõem preferências globais.
  - Critérios de Aceite: Modelo `ConfiguracaoContextual` aceita definições por escopo e substitui valores globais quando disponível.
  - Rastreabilidade: UC-03; Model: Configuracoes.ConfiguracaoContextual

- **RF-10 — Registro de Alterações**
  - Descrição: Todas as alterações nas preferências do usuário são registradas em `ConfiguracaoContaLog`.
  - Critérios de Aceite: Uma entrada de log é criada para cada alteração salva.
  - Rastreabilidade: UC-01; Model: Configuracoes.ConfiguracaoContaLog

- **RF-11 — Visualização e Edição das Preferências**
  - Descrição: O usuário pode visualizar suas preferências atuais e editá-las via formulário ou API.
  - Critérios de Aceite: Formulário exibe os valores atuais e persiste alterações válidas.
  - Rastreabilidade: UC-01; Model: Configuracoes.ConfiguracaoConta

- **RF-12 — API de Preferências**
  - Descrição: O sistema disponibiliza endpoints REST para ler, atualizar e atualizar parcialmente as configurações de conta.
  - Critérios de Aceite: `ConfiguracaoContaViewSet` retorna e persiste dados através do serializer.
  - Rastreabilidade: UC-01; /api/configuracoes/; Model: Configuracoes.ConfiguracaoConta

- **RF-13 — Teste de Notificação**
  - Descrição: O usuário pode acionar endpoint para enviar notificação de teste em canal específico.
  - Critérios de Aceite: Endpoint retorna erro se canal desabilitado e envia mensagem de teste quando habilitado.
  - Rastreabilidade: UC-05; /api/configuracoes/teste/; Model: Configuracoes.ConfiguracaoConta

- **RF-14 — Envio de Resumos Agregados**
  - Descrição: O sistema envia resumos periódicos com contagens de itens pendentes conforme frequência e horários definidos.
  - Critérios de Aceite: Tarefas assíncronas `enviar_notificacoes_diarias` e `enviar_notificacoes_semanais` selecionam usuários elegíveis e disparam resumos.
  - Rastreabilidade: UC-04; Model: Configuracoes.ConfiguracaoConta

## 4. Requisitos Não Funcionais

### Performance
- Carregamento das configurações deve ocorrer em ≤ 100 ms (p95), aproveitando cache de usuário.

### Segurança & LGPD
- O log de alterações deve armazenar IP e user-agent de forma criptografada e consultável por administradores autorizados.
- Criptografar IP e user-agent nos logs de configurações.

### Observabilidade
- Expor métricas de hits/misses de cache e latência de leitura (`config_cache_hits_total`, `config_cache_misses_total`, `config_get_latency_seconds`).
- Expor métricas de cache e latência; definir alertas para taxas de erro de tarefas e p95 de acesso a configurações.

### Acessibilidade & i18n
- ...

### Resiliência
- Garantir relação 1:1 entre `ConfiguracaoConta` e usuário e unicidade de `ConfiguracaoContextual` por usuário + escopo.
- Tarefas de envio de resumos devem executar no minuto configurado pelo usuário com tolerância de ±1 minuto; permitir reenvio em caso de falhas.
- As tarefas de envio de resumos devem garantir entrega confiável, com retries e logs de falhas de integrações externas.

### Arquitetura & Escala
- Todos os modelos deste app devem herdar de `TimeStampedModel`, fornecendo campos `created` e `modified` automaticamente.
- Sempre que aplicável, utilizar `SoftDeleteModel` para exclusão lógica, evitando remoções físicas e permitindo restauração.

## 5. Casos de Uso

### UC‑01 – Configurar Notificações por Canal

1. Usuário acessa a página de configurações ou API.
2. Marca ou desmarca as opções de receber notificações por e‑mail, WhatsApp ou push.
3. Seleciona a frequência para cada canal.
4. Informa horários e dia da semana, se aplicável.
5. Salva as alterações.
6. Sistema valida as entradas, persiste as preferências e registra log.

### UC‑02 – Alternar Tema e Idioma

1. Usuário seleciona o tema (claro, escuro ou automático) e o idioma preferido.
2. Salva as alterações.
3. O sistema atualiza a interface imediatamente (via cookie/localStorage) e persiste a configuração.

### UC‑03 – Configuração Contextual

1. Usuário acessa a página de configurações avançadas.
2. Seleciona o escopo (organização, núcleo ou evento) e define frequências, idioma e tema específicos.
3. Salva as alterações.
4. Sistema cria ou atualiza uma entrada em `ConfiguracaoContextual` e utiliza essas preferências quando o usuário acessa o respectivo escopo.

### UC‑04 – Envio de Resumo Periódico

1. Em horário programado, a tarefa Celery seleciona usuários com frequência “diária” ou “semanal” para o canal correspondente.
2. Calcula contagens de itens pendentes de chat, feed e eventos desde o último envio.
3. Envia e‑mail e/ou mensagem de WhatsApp com o resumo, conforme as preferências.

### UC‑05 – Testar Notificação

1. Usuário chama o endpoint de teste e informa o canal desejado e, opcionalmente, escopo.
2. Sistema verifica se o canal está habilitado nas preferências resolvidas para aquele escopo.
3. Se habilitado, envia uma mensagem de teste utilizando o template correspondente.
4. Retorna sucesso ou erro caso o canal esteja desativado.

## 6. Regras de Negócio

* Cada usuário deve possuir exatamente uma instância de `ConfiguracaoConta` (criada no cadastro).
* As frequências “diária” e “semanal” exigem hora definida; a frequência “semanal” exige também dia da semana.
* Configurações contextuais sobrepõem as configurações globais ao resolver preferências.
* Logs devem ser criados toda vez que o usuário salva alterações de preferências.

## 7. Modelo de Dados

*Nota:* Todos os modelos herdam de `TimeStampedModel` e utilizam `SoftDeleteModel` quando necessário. Campos de timestamp e exclusão lógica não são listados.

### Configuracoes.ConfiguracaoConta
Descrição: Preferências globais do usuário.
Campos:
- `user`: OneToOneField(User)
- `receber_notificacoes_email`: boolean
- `frequencia_notificacoes_email`: enum('imediata','diaria','semanal')
- `receber_notificacoes_whatsapp`: boolean
- `frequencia_notificacoes_whatsapp`: enum
- `receber_notificacoes_push`: boolean
- `frequencia_notificacoes_push`: enum
- `idioma`: enum('pt-BR','en-US','es-ES')
- `tema`: enum('claro','escuro','automatico')
- `hora_notificacao_diaria`: time
- `hora_notificacao_semanal`: time
- `dia_semana_notificacao`: integer
- `deleted`: boolean

### Configuracoes.ConfiguracaoContextual
Descrição: Preferências específicas por escopo.
Campos:
- `user`: ForeignKey(User)
- `escopo_tipo`: enum('organizacao','nucleo','evento')
- `escopo_id`: UUID
- `frequencia_notificacoes_email`: enum
- `frequencia_notificacoes_whatsapp`: enum
- `idioma`: string
- `tema`: enum
- `deleted`: boolean

### Configuracoes.ConfiguracaoContaLog
Descrição: Histórico de alterações de preferências.
Campos:
- `user`: ForeignKey(User)
- `campo`: string
- `valor_antigo`: text
- `valor_novo`: text
- `ip`: encrypted string
- `user_agent`: encrypted string
- `fonte`: enum('UI','API','import')
- `created_at`: datetime

## 8. Critérios de Aceite (Gherkin)

```gherkin
Feature: Notificações push
  Scenario: Usuário desabilita notificações push
    Given usuário autenticado na página de configurações
    When desmarca "receber_notificacoes_push"
    Then a preferência é salva e notificações push deixam de ser enviadas

Feature: Configurar horário semanal
  Scenario: Usuário define resumo semanal às sextas às 09h
    Given frequência_semanal selecionada para email
    When seleciona "sexta-feira" e horário "09:00"
    Then os resumos semanais são enviados somente às 09h das sextas
```

## 9. Dependências e Integrações

* App Accounts – Criação automática de instância de `ConfiguracaoConta` no registro de usuário.
* Django REST Framework – ViewSets e API para acessar e modificar preferências.
* Celery – Tarefas periódicas de envio de resumos diários e semanais.
* Twilio – Envio de mensagens de WhatsApp nas tarefas de resumo semanal ou diário.
* Redis/Cache – Armazenamento das preferências por usuário com métrica de hits/misses e latência.
* Notification Service – Função `enviar_para_usuario` para envio de e-mails dentro das tarefas.

## Anexos e Referências
- ...

## Changelog
- 1.1.0 — 2025-08-13 — Estrutura padronizada e integração das melhorias da versão 1.1
