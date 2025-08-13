---
id: REQ-DISCUSSAO-001
title: Requisitos Discussao Hubx
module: discussao
status: Em vigor
version: "1.1.0"
authors: [preencher@hubx.space]
created: "2025-08-13"
updated: "2025-08-13"
owners: [preencher]
reviewers: [preencher]
tags: [backend, api, frontend, segurança, lgpd]
related_docs: [ADR-001, DIAG-001]
dependencies: [REQ-OUTRO-001]
scope: Discussão (Fórum)
---

## 1. Visão Geral
O módulo de discussão provê um sistema de perguntas e respostas estruturado em **categorias**, **tópicos** e **respostas**. Esta versão atualizada incorpora funcionalidades adicionais observadas no código, como tags, pesquisa full‑text, moderação, anexos e notificações. Os requisitos a seguir substituem a versão 1.0 e servem como referência para desenvolvimento e verificação.

## 2. Escopo
...

## 3. Requisitos Funcionais

### Criação e gestão de categorias
- **RF-01** O sistema deve permitir aos administradores listar, criar, editar e remover categorias. Cada categoria possui nome, descrição, slug e ícone. Ela pode estar associada a uma organização, núcleo ou evento.
- **RF-02** A listagem de categorias deve ser filtrável por contexto (organização, núcleo, evento) e cacheada por 60 segundos para reduzir latência.

### Tópicos de discussão
- **RF-03** Usuários autenticados podem criar tópicos em uma categoria selecionada. Devem ser informados título, descrição (permite Markdown), tags e público alvo. O público alvo pode ser “todos”, “nucleados”, “organizadores” ou “parceiros”.
- **RF-04** Cada tópico deve possuir slug único, data de criação/edição, contagem de visualizações e sinalizadores de **fechado** e **resolvido**. O sistema deve atualizar o slug automaticamente a partir do título.
- **RF-05** O autor ou um administrador pode editar ou excluir seu tópico dentro de um período de 15 minutos após a criação. Após esse período, apenas administradores podem editar ou remover.
- **RF-06** Deve ser possível marcar um tópico como resolvido e indicar a melhor resposta. Somente o autor ou um administrador pode marcar ou desmarcar; ao marcar resolvido, uma notificação deve ser enviada aos participantes. O autor e administradores podem fechar um tópico; apenas administradores podem reabrir.
- **RF-07** Os tópicos podem ser pesquisados por termo de busca. Se estiver usando PostgreSQL, deve empregar busca full‑text; caso contrário, utilizar `icontains`. Deve ser possível ordenar resultados por data de criação, número de respostas ou score (votos).
- **RF-08** Os tópicos devem oferecer filtragem e associação por **tags**. Tags são entidades reutilizáveis gerenciadas pelos administradores.

### Respostas e interações
- **RF-09** Usuários podem responder a um tópico. Cada resposta pode conter texto e opcionalmente anexar um arquivo. Deve ser possível responder a outra resposta (respostas aninhadas) através do campo `reply_to`.
- **RF-10** O autor de uma resposta pode editá‑la ou removê‑la dentro de 15 minutos após sua criação; depois desse prazo, somente administradores podem editar/remover. Ao editar, o sistema deve manter um indicador de que a resposta foi editada e registrar a data da edição.
- **RF-11** O sistema deve permitir que usuários apliquem **votos** (upvote/downvote) em tópicos ou respostas. O modelo genérico de interação deve garantir que um usuário só possa ter um voto por objeto e possibilitar alternar votos. Deve exibir o **score** e a contagem de votos para cada item.
- **RF-12** Usuários podem marcar tópicos ou respostas como inapropriados através de uma **denúncia**. O sistema deve evitar denúncias duplicadas do mesmo usuário para o mesmo objeto. Administradores podem aprovar ou rejeitar denúncias e remover conteúdo; todas as ações de moderação devem ser registradas em um log de moderação.
- **RF-13** Quando houver novas respostas ou um tópico for marcado como resolvido, o sistema deve disparar notificações assíncronas para os participantes por meio de tasks Celery.

### API e integrações
- **RF-14** Deve existir uma API REST para gerenciar categorias, tags, tópicos e respostas. A API deve oferecer endpoints de criação, leitura, edição e exclusão com autenticação e permissões. Ações adicionais: marcar resolvido ou não resolvido, fechar e reabrir, denunciar conteúdo, votar (up/down). A API deve suportar busca, filtros por tags, ordenação e paginação.
- **RF-15** A API deve respeitar os mesmos limites de edição (15 minutos), permissões (autor vs. administrador) e validações de contexto definidos nas views.
- **RF-16** O módulo de discussão deve se integrar ao sistema de notificações para enviar alertas aos participantes e pode se comunicar com o módulo de Agenda para agendar reuniões em decorrência de discussões (recurso futuro).

## 4. Requisitos Não Funcionais

### Performance
- **RNF-01** O sistema deve suportar **pesquisa full‑text** quando a base de dados permitir, retornando resultados em ordem de relevância; caso contrário, deve realizar busca parcial por substring.
- **RNF-02** As listagens de categorias e tópicos devem empregar cache e otimizações (`select_related`, `prefetch_related`) para evitar consultas N+1 e reduzir a latência.

### Segurança & LGPD
- **RNF-03** O sistema deve prevenir spam e abuso, restringindo votos duplicados e denúncias repetidas. Deve validar tipos de arquivo anexados para segurança.

### Observabilidade
- **RNF-04** A aplicação deve registrar logs de moderação e notificações enviadas. Eventos de denúncias e aprovações/rejeições devem ser auditáveis.

### Acessibilidade & i18n
- …

### Resiliência
- **RNF-05** Tarefas assíncronas (envio de notificações) devem ser executadas via Celery, com mecanismo de retry e monitoramento. Os tempos de resposta para notificações devem ser inferiores a alguns segundos.

### Arquitetura & Escala
- **RNF-06** As páginas devem ser responsivas e compatíveis com HTMX para atualizações parciais, proporcionando uma experiência fluida.

## 5. Casos de Uso
- Criar, editar e remover categorias.
- Abrir, responder e moderar tópicos.
- Votar e denunciar conteúdos.
- Pesquisar tópicos por termo e tag.

## 6. Regras de Negócio
- Tópicos e respostas só podem ser editados pelo autor dentro de 15 minutos após a criação.
- Denúncias duplicadas do mesmo usuário para o mesmo objeto são bloqueadas.
- Apenas administradores podem reabrir tópicos fechados.

## 7. Modelo de Dados
### Discussao.CategoriaDiscussao
Descrição: Categoria para organizar tópicos de discussão.
Campos:
- `nome`: …
- `descricao`: …
- `slug`: gerado automaticamente
- `icone`: …
- `organizacao`: …
- `nucleo`: opcional
- `evento`: opcional
- `proprietario`: …
- `administrador`: …

### Discussao.Tag
Descrição: Tag reutilizável para classificar tópicos.
Campos:
- `nome`: único
- `slug`: …

### Discussao.TopicoDiscussao
Descrição: Tópico iniciado por usuário.
Campos:
- `titulo`: …
- `descricao`: …
- `slug`: gerado do título
- `categoria`: …
- `autor`: …
- `publico_alvo`: …
- `fechado`: boolean
- `resolvido`: boolean
- `melhor_resposta`: opcional
- `visualizacoes`: …
- `busca_full_text`: …
- `tags`: M2M Tag
- `nucleo`: opcional
- `evento`: opcional
- `criado_em`: …
- `editado_em`: …

### Discussao.RespostaDiscussao
Descrição: Resposta a um tópico.
Campos:
- `topico`: …
- `autor`: …
- `conteudo`: …
- `reply_to`: opcional
- `anexo`: …
- `editado`: boolean
- `editado_em`: …
- `votos`: …
- `criado_em`: …
- `atualizado_em`: …

### Discussao.InteracaoDiscussao
Descrição: Registro de votos em tópicos e respostas.
Campos:
- `usuario`: …
- `tipo`: upvote/downvote
- `objeto`: referência genérica
- `criado_em`: …
Constraints adicionais:
- unicidade por usuário e objeto

### Discussao.Denuncia
Descrição: Denúncia de conteúdo inapropriado.
Campos:
- `usuario`: …
- `conteudo`: tópico ou resposta
- `motivo`: …
- `estado`: pendente/aprovado/rejeitado
- `criado_em`: …
- `acoes_moderacao`: …

### Discussao.DiscussionModerationLog
Descrição: Log de ações de moderação.
Campos:
- `usuario_moderador`: …
- `conteudo_moderado`: …
- `acao`: …
- `motivo`: …
- `criado_em`: …

## 8. Critérios de Aceite (Gherkin)

### Cenário: Marcar um tópico como resolvido
```gherkin
Dado que um usuário criou um tópico
E uma resposta foi fornecida por outro participante
Quando o autor do tópico marca a resposta como a melhor resposta
Então o tópico passa a estar resolvido
E todos os participantes recebem uma notificação
```

### Cenário: Denunciar uma resposta inadequada
```gherkin
Dado que um usuário visualiza uma resposta com conteúdo ofensivo
Quando ele envia uma denúncia
Então a denúncia fica com status pendente
E um administrador poderá aprovar, rejeitar ou remover a resposta
E as ações ficam registradas em um log de moderação
```

### Cenário: Pesquisar tópicos por palavra e tag
```gherkin
Dado que existem diversos tópicos em uma categoria
Quando um usuário busca por “Banco de Dados” e filtra pela tag “Postgres”
Então são exibidos apenas os tópicos cujo título ou descrição contêm “Banco de Dados” e que possuem a tag “Postgres”
E os resultados são ordenados conforme critérios selecionados (data, votos ou respostas)
```

## 9. Dependências e Integrações
- Sistema de Notificações para envio de alertas.
- Celery para processamento assíncrono.
- Módulo Agenda para criação de reuniões a partir de discussões (futuro).

## Anexos e Referências
...

## Changelog
- 1.1.0 — 2025-08-13 — Normalização estrutural do documento.

