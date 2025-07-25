---
id: REQ-DISCUSSAO-001
title: Requisitos App Discussao Hubx
module: Discussao
status: Em vigor
version: '1.0'
authors: []
created: '2025-07-25'
updated: '2025-07-25'
source:
  - requisitos_app_forum_hubx.pdf
---

## 1. Visão Geral

O App Discussão fornece um fórum colaborativo organizado por categorias, permitindo que usuários criem tópicos, respondam, votem e colaborem de forma estruturada dentro de organizações, núcleos e eventos.

## 2. Escopo
- **Inclui**:
  - Criação, edição e exclusão de categorias.
  - Publicação de tópicos com título e conteúdo.
  - Inserção de respostas em tópicos.
  - Sistema de votações (upvote/downvote).
  - Marcação de tópicos como resolvidos.
  - Gestão de permissões por tipo de usuário.
- **Exclui**:
  - Chat em tempo real (delegado ao App Chat).
  - Integração com redes sociais externas.

## 3. Requisitos Funcionais

- **RF-01**
  - Descrição: Usuário pode visualizar lista de categorias e seus tópicos.
  - Prioridade: Alta
  - Critérios de Aceite: Lista paginada com título e descrição das categorias.

- **RF-02**
  - Descrição: Usuário cria novos tópicos em uma categoria.
  - Prioridade: Alta
  - Critérios de Aceite: Formulário com validação de campos obrigatórios.

- **RF-03**
  - Descrição: Usuário responde a um tópico existente.
  - Prioridade: Alta
  - Critérios de Aceite: Resposta associada corretamente ao tópico e autor.

- **RF-04**
  - Descrição: Usuário vota em tópicos e respostas (upvote/downvote).
  - Prioridade: Média
  - Critérios de Aceite: Voto único por usuário e contagem atualizada em tempo real.

- **RF-05**
  - Descrição: Usuário marca tópico como resolvido se for criador ou admin.
  - Prioridade: Média
  - Critérios de Aceite: Status do tópico atualizado e indicações visuais.

## 4. Requisitos Não-Funcionais

- **RNF-01**
  - Categoria: Desempenho
  - Descrição: Paginação dos tópicos deve responder em p95 ≤ 300 ms.
  - Métrica/Meta: 300 ms

- **RNF-02**
  - Categoria: Usabilidade
  - Descrição: Interface deve ser responsiva em dispositivos móveis.
  - Métrica/Meta: Avaliação em testes de UX

- **RNF-03**
  - Categoria: Segurança
  - Descrição: As ações de criação, edição e exclusão devem validar permissões.
  - Métrica/Meta: 0 acessos indevidos em testes de penetração.

## 5. Casos de Uso

### UC-01 – Gerenciar Categorias
1. Admin ou coordenador acessa seção de categorias.  
2. Cria/edita/exclui categorias.  
3. Sistema persiste alterações e atualiza lista.

### UC-02 – Criar Tópico
1. Usuário seleciona categoria desejada.  
2. Preenche título e conteúdo.  
3. Submete formulário.  
4. Tópico é criado e aparece na lista.

### UC-03 – Responder Tópico
1. Usuário abre tópico.  
2. Digita resposta e envia.  
3. Resposta é salva e aparece em ordem cronológica.

### UC-04 – Votar
1. Usuário clica em upvote/downvote em tópico ou resposta.  
2. Sistema registra e atualiza contagem.

### UC-05 – Marcar Resolução
1. Criador do tópico ou admin clica em “Marcar como Resolvido”.  
2. Sistema define flag `resolved=true` e altera visualização.

## 6. Regras de Negócio
- Cada usuário tem um único voto por item.  
- Apenas criador ou admin pode marcar resolução.  
- Respostas devem herdar contexto organizacional do tópico.

## 7. Modelo de Dados

- **Categoria**  
  - id: UUID  
  - nome: string  
  - descricao: text  
  - organizacao: FK → Organizacao.id  

- **Topico**  
  - id: UUID  
  - categoria: FK → Categoria.id  
  - autor: FK → User.id  
  - titulo: string  
  - conteudo: text  
  - created_at, updated_at: datetime  
  - resolved: boolean  

- **Resposta**  
  - id: UUID  
  - topico: FK → Topico.id  
  - autor: FK → User.id  
  - conteudo: text  
  - created_at: datetime  

- **Voto**  
  - id: UUID  
  - item_type: enum('topico','resposta')  
  - item_id: UUID  
  - user: FK → User.id  
  - vote: integer (1 ou -1)  
  - created_at: datetime  

## 8. Critérios de Aceite (Gherkin)
```gherkin
Feature: Fórum de Discussão
  Scenario: Usuário cria tópico  
    Given usuário autenticado  
    When cria tópico com título "X" e conteúdo "Y"  
    Then tópico aparece na lista da categoria  

  Scenario: Voto em resposta  
    Given resposta existente  
    When usuário clica em upvote  
    Then contagem de votos aumenta em 1
```

## 9. Dependências / Integrações
- **chat.models.User**: autenticação e contexto de usuário.  
- **Organizacoes API**: para filtrar categorias por organização.  
- **Celery**: notificações assíncronas de novos tópicos/respostas.  
- **Search Engine**: índices para busca de tópicos/respostas.  
- **Sentry**: monitoramento de erros.

## 10. Anexos e Referências
- Documento fonte: requisitos_app_forum_hubx.pdf
