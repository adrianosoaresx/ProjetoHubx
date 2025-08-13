---
id: REQ-ORGANIZACOES-001
title: "Requisitos Organizações Hubx Atualizado"
module: Organizacoes
status: Em vigor
version: '1.1'
authors: []
created: '2025-07-25'
updated: '2025-07-29'
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

- **RF-01**
  - Descrição: Listar Organizações com paginação, busca (`search`), filtro `inativa` e ordenação (`ordering`).
  - Critérios de Aceite: `GET /api/organizacoes/?search=<q>&inativa=<bool>&ordering=<campo>&page=<n>` retorna resultados paginados.

- **RF-02**
  - Descrição: Criar nova Organização validando CNPJ e garantindo slug único.
  - Critérios de Aceite: `POST /api/organizacoes/` retorna HTTP 201 ou erro 400 em dados inválidos.

- **RF-03**
  - Descrição: Editar dados de uma Organização existente, registrando logs de mudanças e notificando membros.
  - Critérios de Aceite: `PATCH /api/organizacoes/<id>/` atualiza campos permitidos e gera registros em `OrganizacaoChangeLog` e `OrganizacaoAtividadeLog`.

- **RF-04**
  - Descrição: Excluir Organização (soft delete) apenas pelo usuário root.
  - Critérios de Aceite: `DELETE /api/organizacoes/<id>/` retorna HTTP 204 e marca `deleted`.

- **RF-05**
  - Descrição: Inativar ou reativar Organização, registrando data e logs.
  - Critérios de Aceite: `PATCH /api/organizacoes/<id>/inativar/` ou `/reativar/` retorna HTTP 200 com status atualizado.

- **RF-06**
  - Descrição: Consultar histórico de alterações e atividades, com opção de exportar CSV.
  - Critérios de Aceite: `GET /api/organizacoes/<id>/history/` retorna logs; query `?export=csv` gera arquivo.

- **RF-07**
  - Descrição: Enviar notificações aos membros quando a organização for criada, editada, inativada, reativada ou excluída.
  - Critérios de Aceite: sinal `organizacao_alterada` aciona tarefa Celery `enviar_email_membros`.

- **RF-08** *(Pendente)*
  - Descrição: Associar e remover usuários, núcleos, eventos, empresas e posts à Organização.
  - Critérios de Aceite: endpoints dedicados (`/api/organizacoes/<id>/associados/`, etc.).

## 4. Requisitos Não-Funcionais

- **RNF-01** – Desempenho: p95 das listagens e detalhes ≤ 250 ms. *Pendência de medição.*
- **RNF-02** – Segurança: CRUD protegido por permissões (root para mutações, admin para leitura própria).
- **RNF-03** – Manutenibilidade: cobertura de testes ≥ 90 %. *Pendência.*
- **RNF-04** – Modelos devem herdar `TimeStampedModel`. *Pendência para logs auxiliares.*
- **RNF-05** – Exclusão lógica com `SoftDeleteModel`. *Pendência para logs auxiliares.*
- **RNF-06** – Logs de alterações imutáveis e acessíveis apenas a usuários root.
- **RNF-07** – Cache Redis e uso de `select_related/prefetch_related` para evitar N+1. *Pendência.*
- **RNF-08** – Integração com Sentry para erros e auditoria. *Pendência.*

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

- **Organizacao**
  - id: UUID
  - nome: string
  - cnpj: string
  - descricao: text (opcional)
  - slug: SlugField (único)
  - tipo: string (ong|empresa|coletivo)
  - rua: string
  - cidade: string
  - estado: string
  - contato_nome: string
  - contato_email: email
  - contato_telefone: string
  - avatar: ImageField (opcional)
  - cover: ImageField (opcional)
  - rate_limit_multiplier: float
  - inativa: boolean
  - inativada_em: datetime (opcional)
  - created_by: FK User (opcional)

- **OrganizacaoChangeLog** *(pendente de TimeStamped/SoftDelete)*
  - id: UUID
  - organizacao_id: FK Organizacao
  - campo_alterado: string
  - valor_antigo: text
  - valor_novo: text
  - alterado_por: FK User
  - alterado_em: datetime (auto)

- **OrganizacaoAtividadeLog** *(pendente de TimeStamped/SoftDelete)*
  - id: UUID
  - organizacao_id: FK Organizacao
  - acao: string
  - usuario_id: FK User
  - data: datetime (auto)
  - detalhes: text

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

## 9. Dependências / Integrações

- **App Accounts**: validação de usuário e envio de notificações.
- **Apps Núcleos, Eventos, Empresas, Feed, Discussão**: relacionamentos por organização.
- **Storage S3**: armazenamento de avatar e capa.
- **Celery**: processamento assíncrono de notificações.
- **Sentry**: monitoramento de erros. *Pendência.*

## 10. Requisitos Adicionais / Melhorias

- Implementar endpoints de associação de recursos (RF-08).
- Medir desempenho e cobertura para garantir RNFs.
- Aplicar cache e otimizações de consulta.
- Integrar Sentry e auditoria centralizada.
