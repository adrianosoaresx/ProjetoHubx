---
id: REQ-ORGANIZACOES-001
title: Requisitos Organizações Hubx
module: organizacoes
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

O App Organizações gerencia o ciclo de vida de entidades no Hubx. Permite cadastro completo, inativação, reativação e exclusão lógica, além de manter logs imutáveis de alterações e atividades com notificações aos membros.

## 2. Escopo

- **Inclui**:
  - CRUD de Organizações com campos: nome, cnpj, descrição, slug, tipo, rua, cidade, estado, contatos, avatar, capa, `rate_limit_multiplier`, `inativa`, `inativada_em` e `created_by`.
  - Listagem com busca por nome ou slug, filtro `inativa` e ordenação.
  - Inativar, reativar e excluir organizações (soft delete).
  - Histórico de alterações e atividades com exportação CSV.
  - Notificações assíncronas aos membros quando ocorrerem mudanças.
- **Exclui**:
  - Gestão de permissões avançadas (delegado ao App Accounts).
  - Gestão financeira e de recursos externos.
  - Endpoints específicos para gerenciar associações (realizados em outros módulos). *Pendência: RF-08*.

## 3. Requisitos Funcionais

- **RF-01 — Listar Organizações**
  - Descrição: Listar Organizações com paginação, busca (`search`), filtro `inativa` e ordenação (`ordering`).
  - Critérios de Aceite: `GET /api/organizacoes/?search=<q>&inativa=<bool>&ordering=<campo>&page=<n>` retorna resultados paginados.
  - Rastreabilidade: UC-01; `/api/organizacoes/`; Model: `Organizacoes.Organizacao`

- **RF-02 — Criar Organização**
  - Descrição: Criar nova Organização validando CNPJ e garantindo slug único.
  - Critérios de Aceite: `POST /api/organizacoes/` retorna HTTP 201 ou erro 400 em dados inválidos.
  - Rastreabilidade: UC-02; `/api/organizacoes/`; Model: `Organizacoes.Organizacao`

- **RF-03 — Editar Organização**
  - Descrição: Editar dados de uma Organização existente, registrando logs de mudanças e notificando membros.
  - Critérios de Aceite: `PATCH /api/organizacoes/<id>/` atualiza campos permitidos e gera registros em `OrganizacaoChangeLog` e `OrganizacaoAtividadeLog`.
  - Rastreabilidade: UC-03; `/api/organizacoes/<id>/`; Model: `Organizacoes.OrganizacaoChangeLog`

- **RF-04 — Excluir Organização**
  - Descrição: Excluir Organização (soft delete) apenas pelo usuário root.
  - Critérios de Aceite: `DELETE /api/organizacoes/<id>/` retorna HTTP 204 e marca `deleted`.
  - Rastreabilidade: UC-04; `/api/organizacoes/<id>/`; Model: `Organizacoes.Organizacao`

- **RF-05 — Inativar ou Reativar Organização**
  - Descrição: Inativar ou reativar Organização, registrando data e logs.
  - Critérios de Aceite: `PATCH /api/organizacoes/<id>/inativar/` ou `/reativar/` retorna HTTP 200 com status atualizado.
  - Rastreabilidade: UC-05; `/api/organizacoes/<id>/inativar/`; Model: `Organizacoes.Organizacao`

- **RF-06 — Consultar histórico de alterações e atividades**
  - Descrição: Consultar histórico de alterações e atividades, com opção de exportar CSV.
  - Critérios de Aceite: `GET /api/organizacoes/<id>/history/` retorna logs; query `?export=csv` gera arquivo.
  - Rastreabilidade: UC-06; `/api/organizacoes/<id>/history/`; Model: `Organizacoes.OrganizacaoChangeLog`

- **RF-07 — Notificar membros sobre alterações**
  - Descrição: Enviar notificações aos membros quando a organização for criada, editada, inativada, reativada ou excluída.
  - Critérios de Aceite: sinal `organizacao_alterada` aciona tarefa Celery `enviar_email_membros`.
  - Rastreabilidade: UC-02, UC-03, UC-04, UC-05; signal; Model: `Organizacoes.OrganizacaoAtividadeLog`

- **RF-08 — Associar e remover recursos à Organização** *(Pendente)*
  - Descrição: Associar e remover usuários, núcleos, eventos, empresas e posts à Organização.
  - Critérios de Aceite: endpoints dedicados (`/api/organizacoes/<id>/associados/`, etc.).
  - Rastreabilidade: UC-07; `/api/organizacoes/<id>/associados/`; Model: `Organizacoes.Associacao`

- **RF-09 — Medir desempenho e cobertura**
  - Descrição: Registrar métricas de desempenho e relatórios de cobertura de testes.
  - Critérios de Aceite: métricas p95 e relatórios ≥90% de cobertura disponíveis via pipeline.
  - Rastreabilidade: RNF-01, RNF-06; `/metrics`; Model: `Organizacoes.*`

- **RF-10 — Aplicar cache e otimizações de consulta**
  - Descrição: Aplicar cache Redis e `select_related/prefetch_related` para listagens de organizações.
  - Critérios de Aceite: listagens utilizam cache e evitam N+1; p95 ≤ 250 ms.
  - Rastreabilidade: RNF-02; `/api/organizacoes/`; Model: `Organizacoes.Organizacao`

- **RF-11 — Integrar Sentry e auditoria centralizada**
  - Descrição: Integrar o módulo ao Sentry e ao sistema de auditoria centralizada.
  - Critérios de Aceite: erros e eventos são enviados ao Sentry e audit log.
  - Rastreabilidade: RNF-05; `sentry`; Model: `Organizacoes.*`

## 4. Requisitos Não Funcionais

### Performance
- **RNF-01** Desempenho: p95 das listagens e detalhes ≤ 250 ms.
- **RNF-02** Cache: uso de Redis e `select_related/prefetch_related` para evitar N+1.

### Segurança & LGPD
- **RNF-03** Permissões: CRUD protegido por permissões (root para mutações, admin para leitura própria).
- **RNF-04** Logs imutáveis: alterações acessíveis apenas a usuários root.

### Observabilidade
- **RNF-05** Sentry: integração com Sentry para erros e auditoria.
- **RNF-06** Cobertura: cobertura de testes ≥ 90 % monitorada.

### Acessibilidade & i18n
- **RNF-07** Detalhes de acessibilidade e internacionalização a definir.

### Resiliência
- **RNF-08** Garantir retentativas e idempotência em operações críticas. *(Pendência)*

### Arquitetura & Escala
- **RNF-09** Modelos herdam `TimeStampedModel` e `SoftDeleteModel`.

## 5. Casos de Uso

### UC-01 – Listar Organizações
1. Usuário acessa endpoint de listagem.
2. Aplica busca ou filtros.
3. Sistema retorna lista paginada.

### UC-02 – Criar Organização
1. Usuário root envia dados de nova organização.
2. Sistema valida CNPJ e unicidade de slug.
3. Membros são notificados.

### UC-03 – Editar Organização
1. Usuário root altera dados.
2. Sistema registra logs e notifica membros.

### UC-04 – Excluir Organização
1. Root solicita exclusão via DELETE.
2. Sistema marca como `deleted` e registra log.

### UC-05 – Inativar/Reativar Organização
1. Root chama ação dedicada.
2. Sistema atualiza status e registra log.

### UC-06 – Consultar Histórico
1. Usuário autorizado solicita histórico.
2. Sistema retorna últimas alterações e atividades ou gera CSV.

### UC-07 – Associar Recursos *(Pendente)*
1. Usuário adiciona/remova núcleos, eventos, empresas ou posts.
2. Endpoints atualizam relacionamentos.

## 6. Regras de Negócio

- Slug e CNPJ da organização devem ser únicos e validados.
- Apenas usuários root podem criar, editar, inativar, reativar e excluir organizações.
- Organizações marcadas como `deleted` não aparecem nas buscas.
- Logs de alterações e atividades são imutáveis.

## 7. Modelo de Dados

*Todos os modelos principais usam `TimeStampedModel` e `SoftDeleteModel`, exceto onde indicado.*

### Organizacoes.Organizacao
Descrição: Entidade de organização.
Campos:
- `id`: UUID
- `nome`: string
- `cnpj`: string
- `descricao`: text (opcional)
- `slug`: SlugField — único
- `tipo`: string — `ong|empresa|coletivo`
- `rua`: string
- `cidade`: string
- `estado`: string
- `contato_nome`: string
- `contato_email`: email
- `contato_telefone`: string
- `avatar`: ImageField (opcional)
- `cover`: ImageField (opcional)
- `rate_limit_multiplier`: float
- `inativa`: boolean
- `inativada_em`: datetime (opcional)
- `created_by`: FK → User (opcional)
Constraints adicionais:
- Herda de `TimeStampedModel` e `SoftDeleteModel`

### Organizacoes.OrganizacaoChangeLog
Descrição: Histórico de mudanças.
Campos:
- `id`: UUID
- `organizacao`: FK → Organizacao
- `campo_alterado`: string
- `valor_antigo`: text
- `valor_novo`: text
- `alterado_por`: FK → User
- `alterado_em`: datetime (auto)
Constraints adicionais:
- Pendência de herdar `TimeStampedModel` e `SoftDeleteModel`

### Organizacoes.OrganizacaoAtividadeLog
Descrição: Registro de atividades.
Campos:
- `id`: UUID
- `organizacao`: FK → Organizacao
- `acao`: string
- `usuario`: FK → User
- `data`: datetime (auto)
- `detalhes`: text
Constraints adicionais:
- Pendência de herdar `TimeStampedModel` e `SoftDeleteModel`

## 8. Critérios de Aceite (Gherkin)

```gherkin
Feature: Gestão de Organizações
  Scenario: Usuário root cria organização
    Given usuário root autenticado
    When envia POST com slug e CNPJ válidos
    Then retorna HTTP 201 e organização é criada

  Scenario: Inativar organização
    Given organização existente
    When PATCH /api/organizacoes/<id>/inativar/
    Then status `inativa` é true e log registrado

  Scenario: Exportar histórico
    Given organização com logs
    When GET /api/organizacoes/<id>/history/?export=csv
    Then retorna arquivo CSV com registros
```

## 9. Dependências e Integrações

- **App Accounts**: validação de usuário e envio de notificações.
- **Apps Núcleos, Eventos, Empresas, Feed, Discussão**: relacionamentos por organização.
- **Storage S3**: armazenamento de avatar e capa.
- **Celery**: processamento assíncrono de notificações.
- **Sentry**: monitoramento de erros. *Pendência.*

## Anexos e Referências
...

## Changelog
- 1.1.0 — 2025-08-13 — Normalização estrutural.
