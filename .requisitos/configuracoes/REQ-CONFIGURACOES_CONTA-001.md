---
id: REQ-CONFIGURACOES_CONTA-001
title: "Requisitos Configurações de Conta Hubx"
module: Configuracoes_Conta
status: Em vigor
version: '1.1'
authors: []
created: '2025-07-25'
updated: '2025-08-12'
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

### RF‑01 – Ativar/Desativar Notificações por E‑mail

* Descrição: O usuário pode habilitar ou desabilitar o recebimento de notificações por e‑mail.
* Prioridade: Alta.
* Critério de Aceite: Checkbox salva e reflete estado atual no banco【74186655470974†L44-L55】.

### RF‑02 – Ativar/Desativar Notificações por WhatsApp

* Descrição: O usuário pode habilitar ou desabilitar o recebimento de notificações via WhatsApp.
* Prioridade: Média.
* Critério de Aceite: Estado persistido em `receber_notificacoes_whatsapp`【74186655470974†L50-L55】.

### RF‑03 – Ativar/Desativar Notificações Push

* Descrição: O usuário pode habilitar ou desabilitar o recebimento de notificações push.
* Prioridade: Média.
* Critério de Aceite: Estado persistido em `receber_notificacoes_push`【74186655470974†L56-L61】.

### RF‑04 – Configurar Frequência de Notificações

* Descrição: O usuário pode escolher a frequência das notificações (imediata, diária ou semanal) para cada canal (e‑mail, WhatsApp e push).
* Prioridade: Alta.
* Critério de Aceite: Campos `frequencia_notificacoes_email`, `frequencia_notificacoes_whatsapp` e `frequencia_notificacoes_push` armazenam o valor selecionado【74186655470974†L44-L61】.

### RF‑05 – Escolher Idioma da Interface

* Descrição: Permitir que o usuário selecione o idioma da interface (pt‑BR, en‑US ou es‑ES).
* Prioridade: Média.
* Critério de Aceite: Campo `idioma` salva opção escolhida【74186655470974†L62-L65】.

### RF‑06 – Alternar Tema da Interface

* Descrição: O usuário pode alternar o tema entre claro, escuro e automático (de acordo com o sistema operacional).
* Prioridade: Alta.
* Critério de Aceite: Campo `tema` salva a escolha【74186655470974†L62-L65】.

### RF‑07 – Configurar Horários e Dia da Semana

* Descrição: O usuário pode definir o horário de envio das notificações diárias (`hora_notificacao_diaria`) e o horário e o dia da semana para notificações semanais (`hora_notificacao_semanal` e `dia_semana_notificacao`).
* Prioridade: Média.
* Critério de Aceite: Campos persistidos e validados; hora e dia são obrigatórios quando a frequência diária ou semanal está ativa【74186655470974†L66-L77】【184069624769776†L61-L104】.

### RF‑08 – Configuração Automática no Cadastro

* Descrição: Ao cadastrar um usuário, uma instância de `ConfiguracaoConta` deve ser criada automaticamente.
* Prioridade: Alta.
* Critério de Aceite: Após cadastro, existe instância de `ConfiguracaoConta` associada ao usuário【498180863719394†L16-L33】.

### RF‑09 – Configurações Contextuais por Escopo

* Descrição: O usuário pode criar configurações específicas para um escopo (`organizacao`, `nucleo` ou `evento`) que sobrepõem frequências, idioma e tema globais.
* Prioridade: Média.
* Critério de Aceite: Modelo `ConfiguracaoContextual` aceita definições por escopo e substitui valores globais quando disponível【74186655470974†L88-L116】.

### RF‑10 – Registro de Alterações

* Descrição: Todas as alterações nas preferências do usuário devem ser registradas em `ConfiguracaoContaLog` (campo, valor antigo, valor novo, IP, user‑agent e fonte).
* Prioridade: Média.
* Critério de Aceite: Uma entrada de log é criada para cada alteração salva【74186655470974†L129-L145】.

### RF‑11 – Visualização e Edição das Preferências

* Descrição: O usuário pode visualizar todas as suas preferências atuais e editá‑las através de formulário ou API.
* Prioridade: Alta.
* Critério de Aceite: Formulário exibe os valores atuais e persiste alterações válidas【184069624769776†L61-L104】.

### RF‑12 – API de Preferências

* Descrição: O sistema deve disponibilizar endpoints REST para ler (`GET`), atualizar (`PUT`) e atualizar parcialmente (`PATCH`) as configurações de conta.
* Prioridade: Média.
* Critério de Aceite: `ConfiguracaoContaViewSet` retorna e persiste dados através do serializer【96271031922130†L22-L73】.

### RF‑13 – Teste de Notificação

* Descrição: O usuário pode acionar um endpoint para enviar uma notificação de teste em um canal específico (e‑mail, WhatsApp ou push) e verificar se a configuração está habilitada.
* Prioridade: Baixa.
* Critério de Aceite: Endpoint retorna erro se o canal estiver desabilitado e envia mensagem de teste quando habilitado【96271031922130†L104-L131】.

### RF‑14 – Envio de Resumos Agregados

* Descrição: O sistema deve enviar automaticamente resumos periódicos com contagens agregadas de itens pendentes (notificações de chat, novos posts no feed e eventos) de acordo com a frequência e horários definidos pelo usuário.
* Prioridade: Média.
* Critério de Aceite: Tarefas assíncronas `enviar_notificacoes_diarias` e `enviar_notificacoes_semanais` selecionam usuários elegíveis e disparam resumos por e‑mail ou WhatsApp, respeitando hora e dia configurados【449563910561256†L22-L63】【449563910561256†L83-L89】.

## 4. Requisitos Não‑Funcionais

### RNF‑01 – Desempenho

* Carregamento das configurações deve ocorrer em ≤ 100 ms (p95), aproveitando cache de usuário【498180863719394†L16-L41】.

### RNF‑02 – Confiabilidade

* Garantia de relação 1:1 entre `ConfiguracaoConta` e usuário, e unicidade de `ConfiguracaoContextual` por usuário + escopo【74186655470974†L80-L86】【74186655470974†L120-L127】.

### RNF‑03 – Timestamp Automático

* Todos os modelos deste app devem herdar de `TimeStampedModel`, fornecendo campos `created` e `modified` automaticamente.

### RNF‑04 – Exclusão Lógica

* Sempre que aplicável, utilizar `SoftDeleteModel` para exclusão lógica, evitando remoções físicas e permitindo restauração.

### RNF‑05 – Auditabilidade

* O log de alterações (`ConfiguracaoContaLog`) deve armazenar IP e user‑agent de forma criptografada e deve ser consultável por administradores autorizados【74186655470974†L129-L145】.

### RNF‑06 – Observabilidade

* Expor métricas de hits/misses de cache e latência de leitura (`config_cache_hits_total`, `config_cache_misses_total`, `config_get_latency_seconds`) para monitoramento【498180863719394†L16-L41】.

### RNF‑07 – Tarefas Programadas

* Tarefas de envio de resumos devem executar no minuto configurado pelo usuário com tolerância de ±1 minuto; o sistema deve permitir reenvio em caso de falhas.

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
3. Envia e‑mail e/ou mensagem de WhatsApp com o resumo, conforme as preferências【449563910561256†L22-L63】.

### UC‑05 – Testar Notificação

1. Usuário chama o endpoint de teste e informa o canal desejado e, opcionalmente, escopo.
2. Sistema verifica se o canal está habilitado nas preferências resolvidas para aquele escopo.
3. Se habilitado, envia uma mensagem de teste utilizando o template correspondente【96271031922130†L104-L131】.
4. Retorna sucesso ou erro caso o canal esteja desativado.

## 6. Regras de Negócio

* Cada usuário deve possuir exatamente uma instância de `ConfiguracaoConta` (criada no cadastro)【74186655470974†L80-L86】.
* As frequências “diária” e “semanal” exigem hora definida; a frequência “semanal” exige também dia da semana【74186655470974†L66-L77】【184069624769776†L61-L104】.
* Configurações contextuais sobrepõem as configurações globais ao resolver preferências【498180863719394†L54-L69】.
* Logs devem ser criados toda vez que o usuário salva alterações de preferências【74186655470974†L129-L145】.

## 7. Modelo de Dados

*Nota:* Todos os modelos herdam de `TimeStampedModel` e utilizam `SoftDeleteModel` quando necessário. Campos de timestamp e exclusão lógica não são listados.

**ConfiguracaoConta** 
 -user: OneToOneField(User), 
 -receber_notificacoes_email: boolean, 
 -frequencia_notificacoes_email: enum('imediata','diaria','semanal'), 
 -receber_notificacoes_whatsapp: boolean, 
 -frequencia_notificacoes_whatsapp: enum, 
 -receber_notificacoes_push: boolean, 
 -frequencia_notificacoes_push: enum, 
 -idioma: enum('pt-BR','en-US','es-ES'), 
 -tema: enum('claro','escuro','automatico'), 
 -hora_notificacao_diaria: time, 
 -hora_notificacao_semanal: time, 
 -dia_semana_notificacao: integer, 
 -deleted: boolean`【74186655470974†L44-L77】 

**ConfiguracaoContextual**  
 -user: FK → User, 
 -escopo_tipo: enum('organizacao','nucleo','evento'), 
 -escopo_id: UUID, 
 -frequencia_notificacoes_email: enum, 
 -frequencia_notificacoes_whatsapp: enum, 
 -idioma: string, 
 -tema: enum, 
 -deleted: boolean`【74186655470974†L88-L116】

**ConfiguracaoContaLog** 
 - user: FK → User, 
 - campo: string, 
 -valor_antigo: text, 
 -valor_novo: text, 
 -ip: encrypted string, 
 -user_agent: encrypted string, 
 -fonte: enum('UI','API','import'), 
 -created_at: datetime【74186655470974†L129-L145】

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

## 9. Dependências / Integrações

* **App Accounts** – Criação automática de instância de `ConfiguracaoConta` no registro de usuário.
* **Django REST Framework** – ViewSets e API para acessar e modificar preferências【96271031922130†L22-L73】.
* **Celery** – Tarefas periódicas de envio de resumos diários e semanais【449563910561256†L22-L63】【449563910561256†L83-L89】.
* **Twilio** – Envio de mensagens de WhatsApp nas tarefas de resumo semanal ou diário【449563910561256†L65-L79】.
* **Redis/Cache** – Armazenamento das preferências por usuário com métrica de hits/misses e latência【498180863719394†L16-L41】.
* **Notification Service** – Função `enviar_para_usuario` para envio de e‑mails dentro das tarefas.

## 10. Requisitos Adicionais / Melhorias (v1.1)

### Requisitos Funcionais Adicionais

1. **RF‑15 – Notificações Push** – Adicionar campo `receber_notificacoes_push` e `frequencia_notificacoes_push` para habilitar/desabilitar e configurar frequência de notificações push【74186655470974†L56-L61】.
2. **RF‑16 – Horários de Envio** – Permitir definir horário (`hora_notificacao_diaria` e `hora_notificacao_semanal`) e dia da semana (`dia_semana_notificacao`) para envio de resumos【74186655470974†L66-L77】.
3. **RF‑17 – Configurações Contextuais** – Criar `ConfiguracaoContextual` para permitir preferências por escopo (organização/núcleo/evento)【74186655470974†L88-L116】.
4. **RF‑18 – Logs de Alteração** – Implementar `ConfiguracaoContaLog` para rastrear mudanças de preferências【74186655470974†L129-L145】.
5. **RF‑19 – API de Teste de Notificação** – Disponibilizar endpoint para envio de teste de notificação e verificação de canal【96271031922130†L104-L131】.
6. **RF‑20 – Resumos Agregados** – Implementar tarefas que enviam resumos diários/semanais com contagens de chat, feed e eventos【449563910561256†L22-L63】【449563910561256†L83-L89】.

### Requisitos Não‑Funcionais Adicionais

1. **RNF‑08 – Proteção de Dados** – Criptografar IP e user‑agent nos logs de configurações【74186655470974†L129-L145】.
2. **RNF‑09 – Observabilidade** – Expor métricas de cache e latência; definir alertas para taxas de erro de tarefas e p95 de acesso a configurações【498180863719394†L16-L41】.
3. **RNF‑10 – Confiabilidade de Tarefas** – As tarefas de envio de resumos devem garantir entrega confiável; implementar retries e logs de falhas de integrações externas (Twilio)【449563910561256†L65-L79】.