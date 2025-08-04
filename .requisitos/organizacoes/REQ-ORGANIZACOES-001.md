---
id: REQ-ORGANIZACOES-001
title: Requisitos Organizações Hubx Atualizado
module: Organizacoes
status: Em vigor
version: '1.0'
authors: []
created: '2025-07-25'
updated: '2025-07-25'
source: Requisitos_Organizacoes_Hubx_Atualizado.pdf
---

## 1. Visão Geral

O App Organizações gerencia o ciclo de vida de entidades organizacionais no Hubx, incluindo criação, edição, remoção, visualização de detalhes e associação de usuários e recursos.

## 2. Escopo
- **Inclui**:
  - CRUD completo de Organizações (nome, slug, descrição, avatar e capa).  
  - Listagem e busca por nome e slug.  
  - Visualização de detalhes com avatar e cover.  
  - Associação de usuários, núcleos, eventos, empresas e posts a uma Organização.  
- **Exclui**:
  - Permissões de alto nível (delegado ao App Accounts).  
  - Gestão de recursos externos como faturamento.

## 3. Requisitos Funcionais

- **RF‑01**
  - Descrição: Listar Organizações com paginação e filtros por nome ou slug.
  - Prioridade: Alta
  - Critérios de Aceite: `GET /api/organizacoes/?search=<q>&page=<n>` retorna resultados paginados.

- **RF‑02**
  - Descrição: Criar nova Organização garantindo slug único.
  - Prioridade: Alta
  - Critérios de Aceite: `POST /api/organizacoes/` retorna HTTP 201 e erro 400 em slug duplicado.

- **RF‑03**
  - Descrição: Editar dados de uma Organização existente, incluindo avatar e cover.
  - Prioridade: Média
  - Critérios de Aceite: `PUT/PATCH /api/organizacoes/<id>/` atualiza campos permitidos.

- **RF‑04**
  - Descrição: Excluir Organização (soft delete) pelo usuário root.
  - Prioridade: Baixa
  - Critérios de Aceite: `DELETE /api/organizacoes/<id>/` retorna HTTP 204 e marca flag `deleted`.

- **RF‑05**
  - Descrição: Associar e remover usuários e recursos (núcleos, eventos, empresas, posts) à Organização.
  - Prioridade: Média
  - Critérios de Aceite: Endpoints especializados (`/api/organizacoes/<id>/associados/`, etc.).

## 4. Requisitos Não‑Funcionais

- **RNF‑01**
  - Categoria: Desempenho
  - Descrição: Listagem de Organizações responde em p95 ≤ 250 ms.
  - Métrica/Meta: 250 ms

- **RNF‑02**
  - Categoria: Segurança
  - Descrição: Operações de CRUD são protegidas por permissões adequadas.
  - Métrica/Meta: 0 acessos não autorizados em testes.

- **RNF‑03**
  - Categoria: Manutenibilidade
  - Descrição: Código testável e modular, seguindo DDD.
  - Métrica/Meta: Cobertura de testes ≥ 90 %.


- **RNF‑04**: Todos os modelos deste app devem herdar de `TimeStampedModel` para timestamps automáticos (`created` e `modified`), garantindo consistência e evitando campos manuais.
- **RNF‑05**: Quando houver necessidade de exclusão lógica, os modelos devem implementar `SoftDeleteModel` (ou mixin equivalente), evitando remoções físicas e padronizando os campos `deleted` e `deleted_at`.

## 5. Casos de Uso

### UC‑01 – Listar Organizações
1. Usuário acessa endpoint de listagem.  
2. Aplica busca por nome ou slug.  
3. Sistema retorna lista paginada.

### UC‑02 – Criar Organização
1. Usuário com permissão root envia dados de nova organização.  
2. Sistema valida unicidade de slug.  
3. Retorna HTTP 201 com dados da organização.

### UC‑03 – Editar Organização
1. Usuário autorizado envia alterações.  
2. Sistema atualiza avatar, cover e demais campos.

### UC‑04 – Excluir Organização
1. Root solicita exclusão via DELETE.  
2. Sistema marca organização como `deleted`.

### UC‑05 – Associar Recursos
1. Usuário adiciona/remova núcleos, eventos, empresas ou posts.  
2. Endpoints atualizam relacionamentos.

## 6. Regras de Negócio
- Slug da organização deve ser único.  
- Apenas usuários root podem criar e excluir organizações.  
- Todos os demais recursos devem pertencer a uma organização.  
- Organizações marcadas como `deleted` não aparecem em buscas.

## 7. Modelo de Dados
*Nota:* Todos os modelos herdam de `TimeStampedModel` (campos `created` e `modified`) e utilizam `SoftDeleteModel` para exclusão lógica quando necessário. Assim, campos de timestamp e exclusão lógica não são listados individualmente.

- **Organizacao**  
  - id: UUID  
  - nome: string  
  - slug: SlugField (único)  
  - descricao: text (opcional)  
  - avatar: ImageField (S3, opcional)  
  - cover: ImageField (S3, opcional)  

- **Relacionamentos**  
  - organizacao é ForeignKey em: User, Nucleo, Evento, Empresa, Post, CategoriaForum, TopicoForum, etc.

## 8. Critérios de Aceite (Gherkin)
```gherkin
Feature: Gestão de Organizações
  Scenario: Usuário root cria organização
    Given usuário root autenticado
    When envia POST com slug único
    Then retorna HTTP 201 e organização é criada

  Scenario: Busca por slug
    Given organizações existentes
    When GET /api/organizacoes/?search=hubx
    Then retorna organizações correspondentes
```

## 9. Dependências / Integrações
- **App Accounts**: validação de usuário root.  
- **App Núcleos, Eventos, Empresas, Feed, Discussão**: validação de escopo organizacional.  
- **Storage S3**: armazenamento de imagens.  
- **Celery**: processamento assíncrono de uploads.  
- **Sentry**: monitoramento de erros.

## 10. Anexos e Referências
- Documento fonte: Requisitos_Organizacoes_Hubx_Atualizado.pdf

## 11. Melhorias e Extensões (Auditoria 2025‑07‑25)

### Requisitos Funcionais Adicionais
- **RF‑06** – Enviar notificações aos membros quando ocorrerem alterações significativas (nome, avatar, cover ou exclusão).  
- **RF‑07** – Possibilitar inativar/reativar organizações temporariamente sem remover dados.  
- **RF‑08** – Manter histórico de alterações com controle de versões.  

### Requisitos Não‑Funcionais Adicionais
- **RNF‑06** – Logs de alterações devem ser imutáveis e acessíveis apenas por usuários root.  

### Modelo de Dados Adicional
- `Organizacao`: adicionar `inativa: boolean` e `inativada_em: datetime`.  
- Nova entidade `OrganizacaoLog` com campos: id, organizacao_id, usuario_id, acao, dados_antigos, dados_novos.  