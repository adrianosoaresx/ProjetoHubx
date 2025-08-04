---
id: REQ-FINANCEIRO-002
title: Requisitos Financeiro Hubx
module: Financeiro
status: Em vigor
version: '1.0'
authors: []
created: '2025-07-28'
updated: '2025-07-28'
source: Conversa com cliente
---

## 1. Visão Geral

O módulo Financeiro do Hubx centraliza a gestão de receitas e despesas de núcleos e eventos dentro de uma organização. Ele controla centros de custo, contas de associados, cobranças recorrentes e aportes, além de fornecer relatórios e dashboards com filtros por período, núcleo e evento.

## 2. Escopo
- **Inclui**:
  - Registrar e consolidar pagamentos de mensalidades de associação e de núcleos, bem como ingressos de eventos, via importação de planilhas e lançamentos automáticos.
  - Gerenciamento de centros de custo para núcleos e eventos, incluindo vinculação de eventos a núcleos.
  - Geração de cobranças recorrentes aos associados (mensalidades de associação e de núcleo) com envio automático de notificações.
  - Registro de aportes internos (feito por usuário financeiro) e aportes externos (patrocínios) para núcleos e eventos.
  - Exibição de relatórios e dashboards sobre saldo, receita vs. despesa e evolução de inadimplência e de cada núcleo, com filtros por período ou consolidados.
- **Exclui**:
  - Processamento de pagamentos (interação com gateways de boleto ou Pix) – será tratado pelo sistema de pagamentos.
  - Gestão de organizações, usuários ou núcleos (delegado a outros módulos).

## 3. Requisitos Funcionais

- **RF‑01** – Consolidar Pagamentos
  - **Descrição**: Permitir a importação de planilhas para consolidar pagamentos de mensalidades de associação, mensalidades de núcleos e ingressos de eventos.
  - **Prioridade**: Alta
  - **Critérios de Aceite**: POST `/api/financeiro/importar-pagamentos/` aceita arquivo CSV/XLSX válido, processa registros e atualiza centros de custo e contas dos associados.

- **RF‑02** – Geração de Cobranças Recorrentes
  - **Descrição**: Gerar cobranças mensais para os associados referentes à associação e ao núcleo, com criação de lançamentos financeiros pendentes.
  - **Prioridade**: Alta
  - **Critérios de Aceite**: Tarefa agendada cria registros em `/api/financeiro/lancamentos/` com `tipo=mensalidade_associacao` ou `tipo=mensalidade_nucleo` e envia notificações (e-mail, app e WhatsApp).

- **RF‑03** – Gerenciar Centros de Custo
  - **Descrição**: Criar e editar centros de custo para núcleos e eventos, definindo vinculação de eventos aos seus núcleos e refletindo receitas corretamente.
  - **Prioridade**: Alta
  - **Critérios de Aceite**: POST/PUT `/api/financeiro/centros/` cria/edita centro. Receitas de ingressos são atribuídas de acordo com a vinculação.

- **RF‑04** – Registrar Aportes
  - **Descrição**: Registrar aportes internos feitos pelo usuário financeiro ou externos (patrocínios) em núcleos ou eventos.
  - **Prioridade**: Média
  - **Critérios de Aceite**: POST `/api/financeiro/aportes/` cria registro com valor positivo no centro de custo selecionado.

- **RF‑05** – Visualizar Relatórios e Dashboards
  - **Descrição**: Disponibilizar relatórios e dashboards exibindo saldo do centro de custo, comparativo receita vs. despesa, evolução da inadimplência e evolução financeira de cada núcleo no tempo.
  - **Prioridade**: Alta
  - **Critérios de Aceite**: GET `/api/financeiro/relatorios/?centro=<id>&periodo=YYYY-MM` retorna dados estruturados; dashboards no frontend mostram gráficos com filtros por período ou consolidados.

- **RF‑06** – Gerenciar Inadimplência
  - **Descrição**: Listar lançamentos pendentes (inadimplentes), enviar notificações de atraso e permitir acompanhamento sem aplicar juros ou multas.
  - **Prioridade**: Média
  - **Critérios de Aceite**: GET `/api/financeiro/inadimplencias/` retorna lançamentos pendentes; notificações são disparadas via tarefas agendadas.

## 4. Requisitos Não‑Funcionais

- **RNF‑01**
  - **Categoria**: Desempenho
  - **Descrição**: Listagem de lançamentos e relatórios deve responder em p95 ≤ 300 ms.
  - **Métrica/Meta**: 300 ms

- **RNF‑02**
  - **Categoria**: Segurança
  - **Descrição**: Controle de acesso deve restringir visualização e ações de acordo com o papel (financeiro/admin/coordenador/associado) e escopo organizacional.
  - **Métrica/Meta**: 0 acessos indevidos em testes.

- **RNF‑03**
  - **Categoria**: Escalabilidade
  - **Descrição**: Importação de planilhas deve processar até 10 000 registros em menos de 5 minutos sem degradar a experiência de outros usuários.
  - **Métrica/Meta**: 5 min

- **RNF‑04**
  - **Categoria**: Usabilidade
  - **Descrição**: Interfaces de dashboards devem ser responsivas e acessíveis (seguir padrões WCAG 2.1 nível AA).
  - **Métrica/Meta**: Aderência a auditoria de acessibilidade.


- **RNF‑05**: Todos os modelos deste app devem herdar de `TimeStampedModel` para timestamps automáticos (`created` e `modified`), garantindo consistência e evitando campos manuais.
- **RNF‑06**: Quando houver necessidade de exclusão lógica, os modelos devem implementar `SoftDeleteModel` (ou mixin equivalente), evitando remoções físicas e padronizando os campos `deleted` e `deleted_at`.

## 5. Casos de Uso

### UC‑01 – Importar Pagamentos
1. Usuário financeiro acessa a tela de importação e seleciona uma planilha de pagamentos.
2. Sistema valida o arquivo e exibe prévia dos registros.
3. Usuário confirma a importação.
4. Sistema grava os pagamentos nas contas dos associados e ajusta o saldo dos centros de custo.

### UC‑02 – Gerar Cobranças
1. Tarefa agendada no início do mês cria lançamentos de mensalidade para todos os associados ativos.
2. Sistema envia notificações via e-mail, app e WhatsApp sobre os débitos.
3. Associado visualiza cobrança em sua conta.

### UC‑03 – Registrar Aporte
1. Usuário financeiro seleciona o centro de custo (núcleo ou evento) e informa valor e descrição.
2. Sistema cria registro de aporte e atualiza saldo do centro de custo.

### UC‑04 – Visualizar Relatório
1. Usuário financeiro ou admin escolhe filtros (núcleo/evento/período ou consolidado).
2. Sistema gera relatório com saldo, receitas, despesas, inadimplência e evolução de núcleos.
3. Usuário exporta em CSV ou visualiza no dashboard.

## 6. Regras de Negócio

- O sistema não aplica juros, multas ou suspensões por inadimplência; apenas notifica os associados.
- Eventos vinculados a núcleos devem encaminhar 100 % da receita de ingressos ao centro de custo do núcleo.
- Eventos sem núcleo têm receitas refletidas tanto em seu próprio centro de custo quanto no centro de custo da organização.
- Mensalidades de núcleos creditam diretamente o centro de custo do respectivo núcleo.
- Apenas associados com status ativo podem receber cobranças e fazer pagamentos.
- Lançamentos financeiros não podem ser excluídos; correções devem ser registradas como ajustes.

## 7. Modelo de Dados
*Nota:* Todos os modelos herdam de `TimeStampedModel` (campos `created` e `modified`) e utilizam `SoftDeleteModel` para exclusão lógica quando necessário. Assim, campos de timestamp e exclusão lógica não são listados individualmente.

- **CentroCusto**
  - id: UUID
  - nome: string
  - tipo: enum('organizacao','nucleo','evento')
  - organizacao: FK → Organizacao.id
  - nucleo: FK → Nucleo.id (opcional)
  - evento: FK → Evento.id (opcional)
  - saldo: decimal

- **ContaAssociado**
  - id: UUID
  - user: FK → User.id
  - saldo: decimal

- **LancamentoFinanceiro**
  - id: UUID
  - centro_custo: FK → CentroCusto.id
  - conta_associado: FK → ContaAssociado.id (opcional)
  - tipo: enum('mensalidade_associacao','mensalidade_nucleo','ingresso_evento','aporte_interno','aporte_externo')
  - valor: decimal
  - data_lancamento: datetime
  - status: enum('pendente','pago','cancelado')
  - descricao: text

## 8. Critérios de Aceite (Gherkin)
```gherkin
Feature: Importação de Pagamentos
  Scenario: Usuário financeiro importa planilha de mensalidades
    Given usuário com papel financeiro
    When envia POST para `/api/financeiro/importar-pagamentos/` com planilha válida
    Then retorna HTTP 201 e registros são criados

Feature: Cobrança Recorrente
  Scenario: Sistema gera cobranças mensais
    Given início de mês e associados ativos
    When tarefa agendada executa
    Then lançamentos pendentes são criados e notificações enviadas

Feature: Distribuição de Receitas
  Scenario: Evento pertence a núcleo
    Given evento com centro de custo vinculado a núcleo X
    When pagamento de ingresso é registrado
    Then valor é creditado no centro de custo do núcleo X
```

## 9. Dependências / Integrações
- **App Accounts**: para gestão de usuários e identificação dos associados.
- **App Núcleos**: para validar vínculos entre usuários e núcleos.
- **App Eventos**: para cadastrar eventos e suas vinculações.
- **Sistema de Pagamentos**: integração com gateways de boleto/Pix (em outro módulo).
- **Sistema de Notificações**: envio de e-mails, mensagens no app e WhatsApp.
- **Celery**: para tarefas agendadas (geração de cobranças, envios de avisos).

## 10. Anexos e Referências
- Conversas e instruções do cliente (sprint 2025-07-28).