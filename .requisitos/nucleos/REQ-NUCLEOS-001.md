---
id: REQ-NUCLEOS-001
title: Requisitos Núcleos Hubx
module: Núcleos
status: Em vigor
version: '1.0'
authors: []
created: '2025-07-25'
updated: '2025-07-25'
source: Requisitos_Nucleos_Hubx.pdf
---

## 1. Visão Geral

O App Núcleos gerencia a criação, edição, visualização e associação de usuários a núcleos dentro de uma organização, incluindo imagens de avatar e capa, e controle de membros e coordenadores.

## 2. Escopo
- **Inclui**:
  - CRUD de núcleos (nome, descrição, avatar, capa).  
  - Listagem de núcleos por organização e por usuário.  
  - Associação e remoção de membros via tabela intermediária.  
  - Gestão de coordenadores de núcleo (atribuição e remoção).  
- **Exclui**:
  - Gestão de organizações (delegado ao App Organizações).  
  - Comunicação em tempo real (delegado ao App Chat).

## 3. Requisitos Funcionais

- **RF‑01**
  - Descrição: Criar novo núcleo com nome, descrição, avatar e capa.
  - Prioridade: Alta
  - Critérios de Aceite: POST `/api/nucleos/` retorna HTTP 201 e campos salvos.

- **RF‑02**
  - Descrição: Listar núcleos de uma organização ou de um usuário.
  - Prioridade: Alta
  - Critérios de Aceite: GET `/api/nucleos/?organizacao=<id>` e `/api/users/<id>/nucleos/`.

- **RF‑03**
  - Descrição: Editar dados de um núcleo existente (incluindo avatar/capa).
  - Prioridade: Média
  - Critérios de Aceite: PUT/PATCH `/api/nucleos/<id>/`; arquivos validados.

- **RF‑04**
  - Descrição: Deletar núcleo (soft delete).
  - Prioridade: Média
  - Critérios de Aceite: DELETE `/api/nucleos/<id>/` retorna HTTP 204 e marca `deleted`.

- **RF‑05**
  - Descrição: Adicionar ou remover membros de um núcleo.
  - Prioridade: Alta
  - Critérios de Aceite: POST/DELETE em `/api/nucleos/<id>/membros/`; atualiza tabela ParticipacaoNucleo.

- **RF‑06**
  - Descrição: Atribuir e remover coordenadores de núcleo.
  - Prioridade: Alta
  - Critérios de Aceite: Endpoints `/api/nucleos/<id>/coordenadores/`; somente admins.

## 4. Requisitos Não‑Funcionais

- **RNF‑01**
  - Categoria: Desempenho
  - Descrição: Listagem de núcleos com paginação e filtros responde em p95 ≤ 300 ms.
  - Métrica/Meta: 300 ms

- **RNF‑02**
  - Categoria: Segurança
  - Descrição: Controle de acesso respeita escopo organizacional e permissões.
  - Métrica/Meta: 0 acessos indevidos em testes automatizados.

- **RNF‑03**
  - Categoria: Manutenibilidade
  - Descrição: Código modular e testável seguindo DDD e Clean Architecture.
  - Métrica/Meta: Cobertura de testes ≥ 90 %.

## 5. Casos de Uso

### UC‑01 – Criar Núcleo
1. Usuário com permissão admin envia dados do núcleo.  
2. Sistema valida e cria instância com avatar/capa.  
3. Retorna HTTP 201 com dados do núcleo.

### UC‑02 – Listar Núcleos
1. Usuário acessa listagem por organização ou pelo seu perfil.  
2. Sistema retorna lista paginada.

### UC‑03 – Editar Núcleo
1. Usuário autorizado envia alterações.  
2. Sistema atualiza campos e faz upload de novas mídias.

### UC‑04 – Gerenciar Membros
1. Admin ou coordenador adiciona ou remove usuário.  
2. Endpoint atualiza tabela ParticipacaoNucleo.

### UC‑05 – Gerenciar Coordenadores
1. Admin seleciona usuários para coordenar núcleo.  
2. Permissões de coordenação são atribuídas/removidas.

## 6. Regras de Negócio
- Cada usuário só pode participar de núcleos da sua organização.  
- Um usuário que participa de um núcleo deve ter `is_associado=True`.  
- Coordenador é membro com flag `is_coordenador=True`.  
- Soft delete preserva histórico de associações.

## 7. Modelo de Dados

- **Núcleo**  
  - id: UUID  
  - nome: string  
  - descricao: text (opcional)  
  - avatar: ImageField (S3)  
  - cover: ImageField (S3)  
  - organizacao: FK → Organizacao.id  
  - created_at, updated_at: datetime  

- **ParticipacaoNucleo**  
  - id: UUID  
  - user: FK → User.id  
  - nucleo: FK → Núcleo.id  
  - is_coordenador: boolean  
  - unique_together: (user, nucleo)  

## 8. Critérios de Aceite (Gherkin)
```gherkin
Feature: Gestão de Núcleos
  Scenario: Usuário adiciona membro ao núcleo
    Given usuário com permissão admin
    When envia POST para `/api/nucleos/1/membros/`
    Then retorna HTTP 201 e membro está listado

  Scenario: Coordenação de núcleo
    Given usuário admin
    When cria coordenador via `/api/nucleos/1/coordenadores/`
    Then usuário ganha flag is_coordenador=True
```

## 9. Dependências / Integrações
- **App Accounts**: validação de usuários participantes.  
- **App Organizações**: validação de escopo organizacional.  
- **Storage S3**: armazenamento de avatar e capa.  
- **Celery**: processamento de upload de imagens.  
- **Sentry**: monitoramento de erros.

## 10. Anexos e Referências
- Documento fonte: Requisitos_Nucleos_Hubx.pdf

## 11. Melhorias e Extensões (Auditoria 2025‑07‑25)

### Requisitos Funcionais Adicionais
- **RF‑07** – Implementar fluxo de solicitação de participação com estados `pendente`, `aprovado` e `recusado`. Coordenadores ou admins podem aprovar ou recusar.  
- **RF‑08** – Permitir designar suplentes (coordenadores substitutos) por período determinado.  
- **RF‑09** – Disponibilizar exportação da lista de membros em CSV ou XLS.  

### Modelo de Dados Adicional
- `ParticipacaoNucleo`: adicionar `status: enum('pendente','aprovado','recusado')` e `data_solicitacao: datetime`, `data_decisao: datetime`, `decidido_por: FK → User.id`.  
- Nova entidade `CoordenadorSuplente` com campos: id, nucleo_id, usuario_id, periodo_inicio, periodo_fim.  

### Regras de Negócio Adicionais
- Solicitações pendentes expiram após 30 dias se não forem decididas.  