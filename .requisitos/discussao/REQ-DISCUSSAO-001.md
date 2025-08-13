---
id: REQ-DISCUSSAO-001
version: 1.1
scope: Discussão (Fórum)
updated: 2025-08-12
---

# Requisitos do módulo de Discussão – versão 1.1

## Visão geral

O módulo de discussão provê um sistema de perguntas e respostas estruturado em **categorias**, **tópicos** e **respostas**. Esta versão atualizada incorpora funcionalidades adicionais observadas no código, como tags, pesquisa full‑text, moderação, anexos e notificações. Os requisitos a seguir substituem a versão 1.0 e servem como referência para desenvolvimento e verificação.

## Requisitos funcionais

### Criação e gestão de categorias

- RF‑01 – O sistema deve permitir aos administradores listar, criar, editar e remover categorias. Cada categoria possui nome, descrição, slug e ícone. Ela pode estar associada a uma organização, núcleo ou evento.
- RF‑02 – A listagem de categorias deve ser filtrável por contexto (organização, núcleo, evento) e cacheada por 60 segundos para reduzir latência.

### Tópicos de discussão

- RF‑03 – Usuários autenticados podem criar tópicos em uma categoria selecionada. Devem ser informados título, descrição (permite Markdown), tags e público alvo. O público alvo pode ser “todos”, “nucleados”, “organizadores” ou “parceiros”.
- RF‑04 – Cada tópico deve possuir slug único, data de criação/edição, contagem de visualizações e sinalizadores de **fechado** e **resolvido**. O sistema deve atualizar o slug automaticamente a partir do título.
- RF‑05 – O autor ou um administrador pode editar ou excluir seu tópico dentro de um período de 15 minutos após a criação. Após esse período, apenas administradores podem editar ou remover.
- RF‑06 – Deve ser possível marcar um tópico como resolvido e indicar a melhor resposta. Somente o autor ou um administrador pode marcar ou desmarcar; ao marcar resolvido, uma notificação deve ser enviada aos participantes. O autor e administradores podem fechar um tópico; apenas administradores podem reabrir.
- RF‑07 – Os tópicos podem ser pesquisados por termo de busca. Se estiver usando PostgreSQL, deve empregar busca full‑text; caso contrário, utilizar `icontains`. Deve ser possível ordenar resultados por data de criação, número de respostas ou score (votos).
- RF‑08 – Os tópicos devem oferecer filtragem e associação por **tags**. Tags são entidades reutilizáveis gerenciadas pelos administradores.

### Respostas e interações

- RF‑09 – Usuários podem responder a um tópico. Cada resposta pode conter texto e opcionalmente anexar um arquivo. Deve ser possível responder a outra resposta (respostas aninhadas) através do campo `reply_to`.
- RF‑10 – O autor de uma resposta pode editá‑la ou removê‑la dentro de 15 minutos após sua criação; depois desse prazo, somente administradores podem editar/remover. Ao editar, o sistema deve manter um indicador de que a resposta foi editada e registrar a data da edição.
- RF‑11 – O sistema deve permitir que usuários apliquem **votos** (upvote/downvote) em tópicos ou respostas. O modelo genérico de interação deve garantir que um usuário só possa ter um voto por objeto e possibilitar alternar votos. Deve exibir o **score** e a contagem de votos para cada item.
- RF‑12 – Usuários podem marcar tópicos ou respostas como inapropriados através de uma **denúncia**. O sistema deve evitar denúncias duplicadas do mesmo usuário para o mesmo objeto. Administradores podem aprovar ou rejeitar denúncias e remover conteúdo; todas as ações de moderação devem ser registradas em um log de moderação.
- RF‑13 – Quando houver novas respostas ou um tópico for marcado como resolvido, o sistema deve disparar notificações assíncronas para os participantes por meio de tasks Celery.

### API e integrações

- RF‑14 – Deve existir uma API REST para gerenciar categorias, tags, tópicos e respostas. A API deve oferecer endpoints de criação, leitura, edição e exclusão com autenticação e permissões. Ações adicionais: marcar resolvido ou não resolvido, fechar e reabrir, denunciar conteúdo, votar (up/down). A API deve suportar busca, filtros por tags, ordenação e paginação.
- RF‑15 – A API deve respeitar os mesmos limites de edição (15 minutos), permissões (autor vs. administrador) e validações de contexto definidos nas views.
- RF‑16 – O módulo de discussão deve se integrar ao sistema de notificações para enviar alertas aos participantes e pode se comunicar com o módulo de Agenda para agendar reuniões em decorrência de discussões (recurso futuro).

## Requisitos não funcionais

- RNF‑01 – O sistema deve suportar **pesquisa full‑text** quando a base de dados permitir, retornando resultados em ordem de relevância; caso contrário, deve realizar busca parcial por substring.
- RNF‑02 – As listagens de categorias e tópicos devem empregar cache e otimizações (`select_related`, `prefetch_related`) para evitar consultas N+1 e reduzir a latência.
- RNF‑03 – As páginas devem ser responsivas e compatíveis com HTMX para atualizações parciais, proporcionando uma experiência fluida.
- RNF‑04 – A aplicação deve registrar logs de moderação e notificações enviadas. Eventos de denúncias e aprovações/rejeições devem ser auditáveis.
- RNF‑05 – O sistema deve prevenir spam e abuso, restringindo votos duplicados e denúncias repetidas. Deve validar tipos de arquivo anexados para segurança.
- RNF‑06 – Tarefas assíncronas (envio de notificações) devem ser executadas via Celery, com mecanismo de retry e monitoramento. Os tempos de resposta para notificações devem ser inferiores a alguns segundos.

## Modelos de dados

Em vez de tabelas, listamos as entidades e seus principais campos:

**CategoriaDiscussao** – nome, descrição, slug (gerado automaticamente), ícone, relacionamentos opcionais para Núcleo e Evento, referência à organização e informação de proprietário/administrador.

**Tag** – nome único e slug. As tags podem ser criadas e editadas por administradores e associadas a diversos tópicos.

**TopicoDiscussao** – título, descrição, slug (gerado do título), categoria, autor (usuário), público alvo, indicadores `fechado` e `resolvido`, referência à melhor resposta, contagem de visualizações, campo de busca full‑text, relacionamentos com tags, timestamps de criação e edição, referências opcionais para Núcleo e Evento.

**RespostaDiscussao** – conteúdo da resposta, tópico ao qual pertence, autor, campo `reply_to` para indicar se é resposta a outra resposta, campo para arquivo anexado, indicador de edição (`editado`) e data de edição, contadores de votos, timestamps de criação e edição.

**InteracaoDiscussao** – usuário, tipo de interação (upvote/downvote), relação genérica para apontar para tópico ou resposta, data de criação. Deve existir restrição de unicidade por usuário e objeto.

**Denuncia** – usuário que denuncia, conteúdo denunciado (tópico ou resposta), motivo, estado (pendente, aprovado, rejeitado), data de criação e ações de moderação associadas.

**DiscussionModerationLog** – registra ações de moderação (aprovar, rejeitar, remover), usuário moderador, conteúdo moderado, motivo, e data.

## Cenários de utilização (Gherkin)

**Cenário: Marcar um tópico como resolvido**

```
Dado que um usuário criou um tópico
E uma resposta foi fornecida por outro participante
Quando o autor do tópico marca a resposta como a melhor resposta
Então o tópico passa a estar resolvido
E todos os participantes recebem uma notificação
```

**Cenário: Denunciar uma resposta inadequada**

```
Dado que um usuário visualiza uma resposta com conteúdo ofensivo
Quando ele envia uma denúncia
Então a denúncia fica com status pendente
E um administrador poderá aprovar, rejeitar ou remover a resposta
E as ações ficam registradas em um log de moderação
```

**Cenário: Pesquisar tópicos por palavra e tag**

```
Dado que existem diversos tópicos em uma categoria
Quando um usuário busca por “Banco de Dados” e filtra pela tag “Postgres”
Então são exibidos apenas os tópicos cujo título ou descrição contêm “Banco de Dados” e que possuem a tag “Postgres”
E os resultados são ordenados conforme critérios selecionados (data, votos ou respostas)
```
