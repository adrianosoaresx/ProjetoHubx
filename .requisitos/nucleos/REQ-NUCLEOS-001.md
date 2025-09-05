---
id: REQ-NUCLEOS-001
title: Requisitos Nucleos Hubx
module: nucleos
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

O App Núcleos centraliza a gestão de grupos dentro de uma organização.
Permite criar núcleos com avatar e capa, controlar membros e coordenadores,
emitir convites, acompanhar métricas e gerar relatórios.

## 2. Escopo

- **Inclui**:
  - CRUD de núcleos (nome, descrição, avatar, capa, slug, mensalidade, ativo).
  - Listagem de núcleos por organização com paginação e cache.
  - Solicitação de participação, aprovação, recusa, suspensão e reativação de membros.
  - Emissão e revogação de convites por e‑mail, respeitando cota diária.
  - Aceitação de convites via token.
  - Designação de coordenadores suplentes com período de vigência.
  - Exportação da lista de membros em CSV ou XLS.
  - Publicação de posts no feed do núcleo.
  - Consulta de métricas do núcleo e geração de relatório geral em CSV ou PDF.
- **Exclui**:
  - Gestão de organizações (delegado ao App Organizações).
  - Comunicação em tempo real (delegado ao App Chat).

## 3. Requisitos Funcionais

**RF-01 — Criar núcleo**
- Descrição: Criar novo núcleo com nome, descrição, avatar e capa.
- Critérios de Aceite: POST `/api/nucleos/` retorna HTTP 201 e campos salvos.
- Rastreabilidade: UC-01; `/api/nucleos/`; Model: Nucleos.Nucleo

**RF-02 — Listar núcleos**
- Descrição: Listar núcleos de uma organização com paginação e cache de 5 min.
- Critérios de Aceite: GET `/api/nucleos/?organizacao=<id>` responde com `X-Cache` indicando HIT/MISS.
- Rastreabilidade: UC-02; `/api/nucleos/?organizacao=<id>`; Model: Nucleos.Nucleo

**RF-03 — Editar núcleo**
- Descrição: Editar dados de um núcleo existente, incluindo avatar e capa.
- Critérios de Aceite: PUT/PATCH `/api/nucleos/<id>/` atualiza campos enviados.
- Rastreabilidade: UC-03; `/api/nucleos/<id>/`; Model: Nucleos.Nucleo

**RF-04 — Deletar núcleo**
- Descrição: Deletar núcleo com soft delete.
- Critérios de Aceite: DELETE `/api/nucleos/<id>/` retorna HTTP 204 e marca `deleted`.
- Rastreabilidade: UC-??; `/api/nucleos/<id>/`; Model: Nucleos.Nucleo

**RF-05 — Solicitar participação**
- Descrição: Usuário solicita participação em um núcleo.
- Critérios de Aceite: POST `/api/nucleos/<id>/solicitar/` cria participação com status `pendente`.
- Rastreabilidade: UC-04; `/api/nucleos/<id>/solicitar/`; Model: Nucleos.ParticipacaoNucleo

**RF-06 — Decidir participação**
- Descrição: Admin ou coordenador aprova ou recusa solicitações de participação.
- Critérios de Aceite: POST `/api/nucleos/<id>/membros/<user_id>/aprovar` ou `/recusar` altera o status.
- Rastreabilidade: UC-05; `/api/nucleos/<id>/membros/<user_id>/aprovar`; Model: Nucleos.ParticipacaoNucleo

**RF-07 — Suspender ou reativar membro**
- Descrição: Admin ou coordenador suspende e reativa membros ativos.
- Critérios de Aceite: POST `/api/nucleos/<id>/membros/<user_id>/suspender` ou `/reativar` atualiza `status_suspensao`.
- Rastreabilidade: UC-06; `/api/nucleos/<id>/membros/<user_id>/suspender`; Model: Nucleos.ParticipacaoNucleo

**RF-08 — Gerenciar convites**
- Descrição: Admin gera e revoga convites de participação com cota diária.
- Critérios de Aceite: POST `/api/nucleos/<id>/convites/` cria convite e DELETE `/api/nucleos/<id>/convites/<convite_id>/` revoga.
- Rastreabilidade: UC-07; `/api/nucleos/<id>/convites/`; Model: Nucleos.ConviteNucleo

**RF-09 — Aceitar convite**
- Descrição: Usuário aceita convite de núcleo através de token.
- Critérios de Aceite: GET `/api/nucleos/aceitar-convite/?token=<token>` adiciona usuário ao núcleo se válido.
- Rastreabilidade: UC-??; `/api/nucleos/aceitar-convite/`; Model: Nucleos.ConviteNucleo

**RF-10 — Designar coordenador suplente**
- Descrição: Designar coordenadores suplentes por período determinado.
- Critérios de Aceite: POST `/api/nucleos/<id>/suplentes/` cria suplente; DELETE `/api/nucleos/<id>/suplentes/<id>/` remove.
- Rastreabilidade: UC-08; `/api/nucleos/<id>/suplentes/`; Model: Nucleos.CoordenadorSuplente

**RF-11 — Exportar membros**
- Descrição: Exportar lista de membros do núcleo.
- Critérios de Aceite: GET `/api/nucleos/<id>/membros/exportar?formato=csv|xls` retorna arquivo com dados dos membros.
- Rastreabilidade: UC-09; `/api/nucleos/<id>/membros/exportar`; Model: Nucleos.ParticipacaoNucleo

**RF-12 — Publicar posts**
- Descrição: Membros ativos não suspensos publicam posts no feed do núcleo.
- Critérios de Aceite: POST `/api/nucleos/<id>/posts/` retorna HTTP 201 quando usuário é membro ativo.
- Rastreabilidade: UC-??; `/api/nucleos/<id>/posts/`; Model: Feed.Post

**RF-13 — Consultar status do membro**
- Descrição: Consultar status do usuário autenticado em um núcleo.
- Critérios de Aceite: GET `/api/nucleos/<id>/membro-status/` retorna papel, ativo e suspenso.
- Rastreabilidade: UC-??; `/api/nucleos/<id>/membro-status/`; Model: Nucleos.ParticipacaoNucleo

**RF-14 — Consultar métricas**
- Descrição: Consultar métricas do núcleo.
- Critérios de Aceite: GET `/api/nucleos/<id>/metrics/` retorna totais e opcionalmente membros por status.
- Rastreabilidade: UC-10; `/api/nucleos/<id>/metrics/`; Model: Nucleos.Nucleo

**RF-15 — Gerar relatório geral**
- Descrição: Gerar relatório consolidado de núcleos.
- Critérios de Aceite: GET `/api/nucleos/relatorio?formato=csv|pdf` gera arquivo com métricas de todos os núcleos.
- Rastreabilidade: UC-10; `/api/nucleos/relatorio`; Model: Nucleos.Nucleo

**RF-16 — Gerir coordenadores**
- Descrição: Atribuir e remover coordenadores de núcleo.
- Critérios de Aceite: Endpoints específicos para mudança de papel. *A confirmar.*
- Rastreabilidade: UC-??; `/api/nucleos/<id>/membros/<user_id>/coordenador`; Model: Nucleos.ParticipacaoNucleo

**RF-17 — Listar núcleos do usuário**
- Descrição: Listar núcleos de um usuário autenticado. *A confirmar.*
- Critérios de Aceite: Endpoint de listagem retorna núcleos em que o usuário participa.
- Rastreabilidade: UC-??; `/api/nucleos/meus/`; Model: Nucleos.ParticipacaoNucleo

**RF-18 — Promover ou remover coordenador**
- Descrição: Endpoints para promoção ou remoção de coordenadores existentes.
- Critérios de Aceite: Endpoint promove ou remove papel de coordenador e retorna confirmação.
- Rastreabilidade: UC-??; `/api/nucleos/<id>/membros/<user_id>/promover`; Model: Nucleos.ParticipacaoNucleo

## 4. Requisitos Não Funcionais

**RNF-01 — Desempenho de listagem**
- Categoria: Performance
- Descrição: Listagem de núcleos com paginação e filtros responde em p95 ≤ 300 ms.
- Métrica/Meta: p95 ≤ 300 ms

**RNF-02 — Controle de acesso**
- Categoria: Segurança & LGPD
- Descrição: Controle de acesso respeita escopo organizacional e permissões.
- Métrica/Meta: 0 acessos indevidos em testes automatizados.

**RNF-03 — Código modular testável**
- Categoria: Arquitetura & Escala
- Descrição: Código modular e testável seguindo DDD e Clean Architecture.
- Métrica/Meta: Cobertura de testes ≥ 90 %.

**RNF-04 — Modelos com marcação temporal**
- Categoria: Arquitetura & Escala
- Descrição: Todos os modelos herdam de TimeStampedModel.
- Métrica/Meta: 100% dos modelos com `created_at` e `updated_at`.

**RNF-05 — Suporte a exclusão lógica**
- Categoria: Resiliência
- Descrição: Modelos com exclusão lógica implementam SoftDeleteModel.
- Métrica/Meta: 100% dos modelos que exigem recuperação.

**RNF-06 — Cache em listagens**
- Categoria: Performance
- Descrição: Listagens e métricas utilizam cache com expiração de 5 min.
- Métrica/Meta: TTL de 5 min.

**RNF-07 — Exposição de métricas**
- Categoria: Observabilidade
- Descrição: Métricas de uso são expostas via Prometheus.
- Métrica/Meta: Endpoint `/metrics` disponível.

**RNF-08 — Limite diário de convites**
- Categoria: Segurança & LGPD
- Descrição: Convites por usuário são limitados por cota diária configurável.
- Métrica/Meta: Configuração de cota respeitada 100% das vezes.

## 5. Casos de Uso

### UC‑01 – Criar Núcleo
1. Usuário admin envia dados do núcleo.
2. Sistema valida e cria instância com avatar/capa.
3. Retorna HTTP 201 com dados do núcleo.

### UC‑02 – Listar Núcleos
1. Usuário filtra por organização.
2. Sistema retorna lista paginada com indicador de cache.

### UC‑03 – Editar Núcleo
1. Usuário autorizado envia alterações.
2. Sistema atualiza campos e faz upload de novas mídias.

### UC‑04 – Solicitar Participação
1. Usuário envia solicitação para um núcleo.
2. Sistema registra participação com status `pendente`.

### UC‑05 – Decidir Participação
1. Admin ou coordenador aprova ou recusa solicitação.
2. Sistema atualiza status e notifica o usuário.

### UC‑06 – Gerenciar Membro Ativo
1. Admin ou coordenador suspende ou reativa membro.
2. Sistema ajusta cobranças e registra data de suspensão.

### UC‑07 – Emitir Convite
1. Admin solicita criação de convite.
2. Sistema verifica cota diária e gera token enviado por e‑mail.

### UC‑08 – Designar Suplente
1. Admin ou coordenador informa usuário e período.
2. Sistema valida sobreposições e cria suplência.

### UC‑09 – Exportar Membros
1. Admin ou coordenador requisita exportação.
2. Sistema gera arquivo CSV ou XLS e notifica membros.

### UC‑10 – Consultar Métricas
1. Usuário solicita métricas de um núcleo.
2. Sistema retorna totais de membros, suplentes e taxa de participação.

## 6. Regras de Negócio

- Cada usuário só participa de núcleos da sua organização.
- Solicitações pendentes expiram após 30 dias.
- Convites expiram em 7 dias e respeitam limite diário.
- Suspenso não pode publicar nem é contabilizado como ativo.
- Coordenador suplente é válido apenas dentro do período informado.
- Soft delete preserva histórico de associações.
- Definir política para exclusão de membros (remoção definitiva vs. status inativo).

## 7. Modelo de Dados

*Todos os modelos abaixo herdam de `TimeStampedModel` e `SoftDeleteModel` quando aplicável.*

### Nucleos.Nucleo
Descrição: Núcleo dentro de uma organização
Campos:
- `id`: UUID
- `organizacao`: FK → Organizacao.id
- `nome`: string
- `slug`: string
- `descricao`: text — opcional
- `avatar`: ImageField — S3
- `cover`: ImageField — S3
- `ativo`: boolean
- `mensalidade`: decimal

### Nucleos.ParticipacaoNucleo
Descrição: Vínculo entre usuário e núcleo
Campos:
- `id`: UUID
- `user`: FK → User.id
- `nucleo`: FK → Nucleos.Nucleo.id
- `papel`: enum('membro','coordenador')
- `status`: enum('pendente','ativo','inativo')
- `status_suspensao`: boolean
- `data_suspensao`: datetime
- `data_solicitacao`: datetime
- `data_decisao`: datetime
- `decidido_por`: FK → User.id
- `justificativa`: text
Constraints adicionais:
- `unique_together (user, nucleo)`

### Nucleos.CoordenadorSuplente
Descrição: Coordenador substituto temporário
Campos:
- `id`: UUID
- `nucleo`: FK → Nucleos.Nucleo.id
- `usuario`: FK → User.id
- `periodo_inicio`: datetime
- `periodo_fim`: datetime

### Nucleos.ConviteNucleo
Descrição: Convite de participação no núcleo
Campos:
- `id`: UUID
- `token`: string
- `token_obj`: FK → TokenAcesso.id
- `email`: email
- `papel`: enum('membro','coordenador')
- `limite_uso_diario`: integer
- `data_expiracao`: datetime
- `usado_em`: datetime
- `criado_em`: datetime
- `nucleo`: FK → Nucleos.Nucleo.id

## 8. Critérios de Aceite (Gherkin)

```gherkin
Feature: Gestão de Núcleos
  Scenario: Usuário aceita convite válido
    Given usuário autenticado com e-mail igual ao do convite
    When acessa `/api/nucleos/aceitar-convite/?token=123`
    Then participa do núcleo com status ativo

  Scenario: Suspensão de membro
    Given admin autenticado
    When envia POST para `/api/nucleos/1/membros/2/suspender`
    Then participação fica com `status_suspensao=True`
```

## 9. Dependências e Integrações

- **App Accounts**: validação de usuários participantes.
- **App Organizações**: escopo organizacional.
- **App Feed**: criação de posts de núcleo.
- **App Financeiro**: ajuste de cobranças ao suspender/reativar.
- **App Notificações**: envio de mensagens assíncronas.
- **App Tokens**: geração de tokens para convites.
- **App Eventos**: dados usados no relatório geral.
- **Storage S3**: armazenamento de avatar e capa.
- **Celery**: processamento assíncrono de notificações e expirações.
- **Sentry/Prometheus**: monitoramento de erros e métricas.

## Anexos e Referências
...

## Changelog
- 1.1.0 — 2025-08-13 — Normalização para Padrão Unificado v3.1

