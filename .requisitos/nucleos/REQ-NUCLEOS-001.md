---
id: REQ-NUCLEOS-001
title: "Requisitos Núcleos Hubx"
module: "Núcleos"
status: Em vigor
version: '1.1'
authors: []
created: '2025-07-25'
updated: '2025-08-13'
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

- **RF‑01**
  - Descrição: Criar novo núcleo com nome, descrição, avatar e capa.
  - Prioridade: Alta
  - Critérios de Aceite: POST `/api/nucleos/` retorna HTTP 201 e campos salvos.

- **RF‑02**
  - Descrição: Listar núcleos de uma organização com paginação e cache de 5 min.
  - Prioridade: Alta
  - Critérios de Aceite: GET `/api/nucleos/?organizacao=<id>` responde com `X‑Cache` indicando HIT/MISS.

- **RF‑03**
  - Descrição: Editar dados de um núcleo existente (incluindo avatar/capa).
  - Prioridade: Média
  - Critérios de Aceite: PUT/PATCH `/api/nucleos/<id>/` atualiza campos enviados.

- **RF‑04**
  - Descrição: Deletar núcleo (soft delete).
  - Prioridade: Média
  - Critérios de Aceite: DELETE `/api/nucleos/<id>/` retorna HTTP 204 e marca `deleted`.

- **RF‑05**
  - Descrição: Usuário solicita participação em um núcleo.
  - Prioridade: Alta
  - Critérios de Aceite: POST `/api/nucleos/<id>/solicitar/` cria participação com status `pendente`.

- **RF‑06**
  - Descrição: Admin ou coordenador aprova ou recusa solicitações de participação.
  - Prioridade: Alta
  - Critérios de Aceite: POST `/api/nucleos/<id>/membros/<user_id>/aprovar` ou `/recusar` altera o status.

- **RF‑07**
  - Descrição: Admin ou coordenador suspende e reativa membros ativos.
  - Prioridade: Média
  - Critérios de Aceite: POST `/api/nucleos/<id>/membros/<user_id>/suspender` ou `/reativar` atualiza `status_suspensao`.

- **RF‑08**
  - Descrição: Admin gera e revoga convites de participação com cota diária.
  - Prioridade: Média
  - Critérios de Aceite: POST `/api/nucleos/<id>/convites/` cria convite e DELETE `/api/nucleos/<id>/convites/<convite_id>/` revoga.

- **RF‑09**
  - Descrição: Usuário aceita convite de núcleo através de token.
  - Prioridade: Média
  - Critérios de Aceite: GET `/api/nucleos/aceitar-convite/?token=<token>` adiciona usuário ao núcleo se válido.

- **RF‑10**
  - Descrição: Designar coordenadores suplentes por período determinado.
  - Prioridade: Média
  - Critérios de Aceite: POST `/api/nucleos/<id>/suplentes/` cria suplente; DELETE `/api/nucleos/<id>/suplentes/<id>/` remove.

- **RF‑11**
  - Descrição: Exportar lista de membros do núcleo.
  - Prioridade: Baixa
  - Critérios de Aceite: GET `/api/nucleos/<id>/membros/exportar?formato=csv|xls` retorna arquivo com dados dos membros.

- **RF‑12**
  - Descrição: Membros ativos não suspensos publicam posts no feed do núcleo.
  - Prioridade: Baixa
  - Critérios de Aceite: POST `/api/nucleos/<id>/posts/` retorna HTTP 201 quando usuário é membro ativo.

- **RF‑13**
  - Descrição: Consultar status do usuário autenticado em um núcleo.
  - Prioridade: Baixa
  - Critérios de Aceite: GET `/api/nucleos/<id>/membro-status/` retorna papel, ativo e suspenso.

- **RF‑14**
  - Descrição: Consultar métricas do núcleo.
  - Prioridade: Baixa
  - Critérios de Aceite: GET `/api/nucleos/<id>/metrics/` retorna totais e opcionalmente membros por status.

- **RF‑15**
  - Descrição: Gerar relatório consolidado de núcleos.
  - Prioridade: Baixa
  - Critérios de Aceite: GET `/api/nucleos/relatorio?formato=csv|pdf` gera arquivo com métricas de todos os núcleos.

- **RF‑16**
  - Descrição: Atribuir e remover coordenadores de núcleo.
  - Prioridade: Média
  - Critérios de Aceite: Endpoints específicos para mudança de papel. *A confirmar.*

## 4. Requisitos Não‑Funcionais

- **RNF‑01**
  - Categoria: Desempenho
  - Descrição: Listagem de núcleos com paginação e filtros responde em p95 ≤ 300 ms.
  - Métrica/Meta: 300 ms

- **RNF‑02**
  - Categoria: Segurança
  - Descrição: Controle de acesso respeita escopo organizacional e permissões.
  - Métrica/Meta: 0 acessos indevidos em testes automatizados.

- **RNF‑03**
  - Categoria: Manutenibilidade
  - Descrição: Código modular e testável seguindo DDD e Clean Architecture.
  - Métrica/Meta: Cobertura de testes ≥ 90 %.

- **RNF‑04**: Todos os modelos herdam de `TimeStampedModel`.
- **RNF‑05**: Modelos com exclusão lógica implementam `SoftDeleteModel`.
- **RNF‑06**: Listagens e métricas utilizam cache com expiração de 5 min.
- **RNF‑07**: Métricas de uso são expostas via Prometheus.
- **RNF‑08**: Convites por usuário são limitados por cota diária configurável.

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

## 7. Modelo de Dados

*Todos os modelos abaixo herdam de `TimeStampedModel` e `SoftDeleteModel` quando aplicável.*

- **Núcleo**
  - id: UUID
  - organizacao: FK → Organizacao.id
  - nome: string
  - slug: string
  - descricao: text (opcional)
  - avatar: ImageField (S3)
  - cover: ImageField (S3)
  - ativo: boolean
  - mensalidade: decimal

- **ParticipacaoNucleo**
  - id: UUID
  - user: FK → User.id
  - nucleo: FK → Núcleo.id
  - papel: enum('membro','coordenador')
  - status: enum('pendente','ativo','inativo')
  - status_suspensao: boolean
  - data_suspensao: datetime
  - data_solicitacao: datetime
  - data_decisao: datetime
  - decidido_por: FK → User.id
  - justificativa: text
  - unique_together: (user, nucleo)

- **CoordenadorSuplente**
  - id: UUID
  - nucleo: FK → Núcleo.id
  - usuario: FK → User.id
  - periodo_inicio: datetime
  - periodo_fim: datetime

- **ConviteNucleo**
  - id: UUID
  - token: string
  - token_obj: FK → TokenAcesso.id
  - email: email
  - papel: enum('membro','coordenador')
  - limite_uso_diario: integer
  - data_expiracao: datetime
  - usado_em: datetime
  - criado_em: datetime
  - nucleo: FK → Núcleo.id

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

## 9. Dependências / Integrações

- **App Accounts**: validação de usuários participantes.
- **App Organizações**: escopo organizacional.
- **App Feed**: criação de posts de núcleo.
- **App Financeiro**: ajuste de cobranças ao suspender/reativar.
- **App Notificações**: envio de mensagens assíncronas.
- **App Tokens**: geração de tokens para convites.
- **App Agenda**: dados usados no relatório geral.
- **Storage S3**: armazenamento de avatar e capa.
- **Celery**: processamento assíncrono de notificações e expirações.
- **Sentry/Prometheus**: monitoramento de erros e métricas.

## 10. Requisitos Adicionais / Melhorias

### Requisitos Funcionais
- **RF‑17** – Listar núcleos de um usuário autenticado. *A confirmar.*
- **RF‑18** – Endpoints para promoção ou remoção de coordenadores existentes.

### Regras de Negócio
- Definir política para exclusão de membros (remoção definitiva vs. status inativo).

