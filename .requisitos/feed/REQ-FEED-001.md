---
id: REQ-FEED-001
title: Requisitos Feed Hubx
module: feed
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

O módulo Feed provê um mural de publicações que permite a usuários e organizações compartilhar textos e mídias com diferentes escopos (global, usuário, núcleo ou evento). Esta versão atualizada inclui funcionalidades de moderação automática, denúncias, comentários, curtidas, favoritos, reações, notificações, rate limiting, caching e coleta de métricas, além dos requisitos básicos de 1.0.

## 2. Escopo

- **Inclui**:
  - Listagem de posts por tipo de feed com filtros por organização, núcleo, evento, tags e datas.
  - Criação, edição e remoção (soft delete) de posts contendo texto e um arquivo de mídia (imagem, PDF ou vídeo) com validação de tipo e tamanho.
  - Upload e download de arquivos através de storage externo (S3) com geração de URL assinada.
  - Sistema de tags para categorização de posts e filtragem.
  - Sistema de moderação: análise automatizada de conteúdo, denúncias de usuários e moderação manual por administradores.
  - Comentários com suporte a respostas aninhadas, curtidas, bookmarks, reações (curtida/compartilhamento) e registro de visualizações.
  - Notificações para novos posts, interações (curtidas e comentários) e decisões de moderação.
  - Rate limiting por usuário e organização para criação e leitura de posts.
  - Cache de listagens e coleta de métricas Prometheus (contadores e histogramas).
  - Configuração de plugins por organização para posts automatizados.
- **Exclui**:
  - Chat em tempo real (delegado ao App Chat).
  - Pagamentos e integrações financeiras.

## 3. Requisitos Funcionais

### Posts e mídia

- **RF-01** Listar posts conforme `tipo_feed` (global, usuário, núcleo, evento) com filtros por organização, núcleo, evento, tags, data de criação e busca textual. A resposta deve ser paginada via `GET /api/feed/`.
- **RF-02** Criar post com texto opcional e uma única mídia (imagem, PDF ou vídeo). O backend deve validar o tipo e tamanho da mídia conforme configuração. Campos obrigatórios: `tipo_feed`, `conteudo` ou mídia, `organizacao`; `nucleo` é obrigatório se `tipo_feed` = "nucleo" e `evento` se `tipo_feed` = "evento".
- **RF-03** Editar post existente pelo autor, administradores ou moderadores, respeitando as mesmas validações de criação.
- **RF-04** Excluir post através de soft delete. O post não aparece em listagens enquanto `deleted=True`.
- **RF-05** Filtrar posts por tags e intervalos de data; combinar busca textual em `conteudo` e `tags__nome` com operadores OR (`|`). A busca deve usar full-text (PostgreSQL) ou fallback `icontains`.
- **RF-06** Upload de arquivos resiliente: o upload deve armazenar o arquivo em S3 (ou storage configurado), validar tamanho e extensão e retornar chave interna; URLs assinadas para download devem expirar em 1 hora.
- **RF-07** Suportar vídeos (MP4/WebM) com preview e reprodução embutida. Limite de tamanho definido por configuração.

### Tags e categorização

- **RF-08** Criar, editar, listar e excluir tags associadas a posts. Cada tag possui nome único. Os usuários podem selecionar múltiplas tags ao publicar.

### Moderação e denúncias

- **RF-09** Aplicar moderação automática usando heurísticas de palavras proibidas. O sistema deve classificar conteúdos como “aprovado”, “pendente” ou “rejeitado”. Posts “rejeitados” não são salvos.
- **RF-10** Permitir que usuários denunciem posts. Cada usuário pode denunciar um post uma vez; ao atingir um limite configurável de denúncias (padrão 3), o status de moderação deve passar para “pendente” com motivo “Limite de denúncias atingido”.
- **RF-11** Moderadores devem poder aprovar ou rejeitar posts pendentes, registrando o usuário avaliador, motivo e data. Posts aprovados tornam-se visíveis; posts rejeitados permanecem ocultos.
- **RF-12** Manter histórico de moderação em `ModeracaoPost` com status atual, motivo, avaliador e data.

### Interações e engajamento

- **RF-13** Permitir curtidas (Like) em posts. Curtir novamente remove a curtida (toggle). Registrar apenas uma curtida por usuário por post.
- **RF-14** Permitir bookmarks (salvar) de posts; listar posts favoritos de cada usuário.
- **RF-15** Permitir comentários em posts com suporte a respostas aninhadas (`reply_to`). Comentários devem estar disponíveis via API e interface, com criação e remoção controladas por permissões.
- **RF-16** Permitir reações adicionais (curtida e compartilhamento) em posts registradas em `Reacao` (um tipo por usuário por post).
- **RF-17** Registrar visualizações de posts (abertura e fechamento) por usuário, incluindo tempo de leitura, para métricas e sugestões futuras.

### Notificações e tarefas assíncronas

- **RF-18** Enviar notificações para todos os usuários da organização (exceto o autor) quando um novo post é criado (`feed_new_post`). Garantir idempotência em 1 hora.
- **RF-19** Enviar notificações ao autor quando seu post receber uma curtida (`feed_like`) ou um comentário (`feed_comment`).
- **RF-20** Enviar notificações ao autor quando um post for moderado, indicando o status final (`feed_post_moderated`).
- **RF-21** Registrar métricas de posts criados (`POSTS_CREATED`), notificações enviadas (`NOTIFICATIONS_SENT`) e latência do envio (`NOTIFICATION_LATENCY`).
- **RF-22** Configurar plugins de feed por organização (`FeedPluginConfig`) definindo o módulo Python responsável e a frequência de execução. Plugins podem criar posts automaticamente em intervalos definidos.

### API e integrações

- **RF-23** Oferecer API REST com endpoints para posts, comentários, curtidas, bookmarks, denúncias e moderação. A API deve suportar filtros, busca textual, ordenação e paginação, além de endpoints específicos para actions (bookmark/unbookmark, denunciar, moderar) e detalhes de visualizações.
- **RF-24** Respeitar rate limits configuráveis: cada usuário tem um número máximo de posts criados e leituras de feed por período, ajustável por multiplicador de organização.
- **RF-25** Integrar com Celery para processar uploads, notificações e moderação assíncrona. As tasks devem registrar falhas no Sentry e realizar retry em caso de erros temporários.

## 4. Requisitos Não Funcionais

### Performance
- **RNF-01** Desempenho: listagem e paginação do feed devem responder em p95 ≤ 300 ms. Utilizar `select_related` e `prefetch_related`, índices apropriados e cache de resultados.

### Segurança & LGPD
- **RNF-02** Segurança: controle de acesso baseado em escopo e permissões; aplicar rate limiting para prevenir abuso; sanitizar entradas de texto; restringir tipos de arquivo e tamanho; registrar ações de moderação para auditoria.

### Observabilidade
- **RNF-03** Observabilidade: integrar métricas Prometheus (counters, histograms) e logging estruturado; monitorar falhas via Sentry; uso de `PostView` para análise de engajamento.

### Acessibilidade & i18n
- **RNF-04** Usabilidade: páginas devem ser responsivas e utilizarem HTMX para atualização parcial; validar formulários no lado cliente e servidor, exibindo mensagens claras.

### Resiliência
- **RNF-05** Confiabilidade: uploads de arquivos devem ser resilientes a falhas de rede, com até 3 retries; tasks assíncronas devem garantir idempotência (ex.: `notify_new_post`).

### Arquitetura & Escala
- **RNF-06** Persistência: todos os modelos herdam de `TimeStampedModel` para timestamps e `SoftDeleteModel` para exclusão lógica, exceto as tabelas de métricas.
- **RNF-07** Escalabilidade: suporte a caching configurável (Redis) para listagens populares; índices full-text para PostgreSQL; fallback eficiente para outras bases.

## 5. Casos de Uso

### UC-01 – Listar Feed
1. Usuário acessa endpoint de listagem com parâmetros (`tipo_feed`, `organizacao`, `nucleo`, `evento`, `tags`, `date_from`, `date_to`, `q`).
2. Sistema verifica permissões e aplica filtros de escopo.
3. Busca full-text ou fallback se aplicável; resultados são ordenados por relevância ou data de criação.
4. Posts são retornados paginados, vindo do cache quando disponível.

### UC-02 – Criar Post
1. Usuário envia `conteudo`, `tipo_feed` e opcionalmente um arquivo.
2. Backend valida campos obrigatórios e mídia; analisa o conteúdo via IA (`pre_analise`).
3. Se a decisão for “rejeitado”, retorna erro; senão, salva o post, aplica decisão de moderação e envia notificações aos usuários da organização.
4. Retorna HTTP 201 com os dados do post.

### UC-03 – Interagir com Post
1. Usuário consulta um post e pode curtir, comentar, reagir ou salvar.
2. Para curtidas e comentários, tasks assíncronas notificam o autor.
3. Para denúncias, registra‐se um `Flag`; se o limite for atingido, muda o status de moderação para “pendente”.
4. Bookmarks são armazenados ou removidos e podem ser listados via endpoint.

### UC-04 – Moderar Post
1. Moderador acessa o painel de moderação e aprova ou rejeita posts pendentes.
2. Sistema atualiza o status e registra motivo, avaliador e data.
3. Uma task assíncrona envia notificação ao autor informando a decisão.

## 6. Regras de Negócio

- O campo `organizacao` é obrigatório para todos os posts.
- Para `tipo_feed` = "nucleo", o `nucleo` deve ser especificado e o autor deve ser membro desse núcleo; para `tipo_feed` = "evento", o `evento` deve ser especificado.
- Apenas um arquivo de mídia pode ser enviado por post; se múltiplos forem enviados, o sistema rejeita a requisição.
- Posts moderados como "rejeitado" ou "pendente" não aparecem no feed público; somente o autor e moderadores podem visualizá-los.
- Denúncias duplicadas pelo mesmo usuário são rejeitadas. O limite de denúncias que coloca um post em revisão é configurável (`FEED_FLAGS_LIMIT`).
- Curtidas são exclusivas por par (`user`, `post`); reações são exclusivas por par (`user`, `post`, `tipo`).
- Cada comentário pode referenciar outro comentário (`reply_to`), formando árvore; a ordem de exibição é cronológica.
- Rate limits por usuário são configuráveis (`FEED_RATE_LIMIT_POST`, `FEED_RATE_LIMIT_READ`) e multiplicados pelo fator da organização.
- Plugins de feed podem criar posts automáticos conforme frequência configurada em `FeedPluginConfig`.

## 7. Modelo de Dados

### Feed.Post
Descrição: Publicação do feed.
Campos:
- `id`: …
- `autor`: FK → User
- `organizacao`: FK → Organizacao
- `tipo_feed`: …
- `nucleo`: FK → Nucleo (opcional)
- `evento`: FK → Evento (opcional)
- `conteudo`: …
- `image`: opcional
- `pdf`: opcional
- `video`: opcional
- `tags`: M2M → Tag
- `deleted`: bool
Constraints adicionais:
- Herda de `TimeStampedModel` e `SoftDeleteModel`

### Feed.Tag
Descrição: Tag para categorizar posts.
Campos:
- `id`: …
- `nome`: …
Constraints adicionais:
- Herda de `TimeStampedModel`

### Feed.ModeracaoPost
Descrição: Histórico de moderação.
Campos:
- `id`: …
- `post`: OneToOne → Post
- `status`: `pendente` | `aprovado` | `rejeitado`
- `motivo`: …
- `avaliado_por`: FK → User (opcional)
- `avaliado_em`: datetime
Constraints adicionais:
- Herda de `TimeStampedModel`

### Feed.Flag
Descrição: Denúncia de post.
Campos:
- `id`: …
- `post`: FK → Post
- `user`: FK → User
Constraints adicionais:
- Herda de `TimeStampedModel`

### Feed.Like
Descrição: Curtida em post.
Campos:
- `id`: …
- `post`: FK → Post
- `user`: FK → User
Constraints adicionais:
- Herda de `TimeStampedModel`

### Feed.Bookmark
Descrição: Post salvo por usuário.
Campos:
- `id`: …
- `user`: FK → User
- `post`: FK → Post
Constraints adicionais:
- Herda de `TimeStampedModel`

### Feed.Comment
Descrição: Comentário em post.
Campos:
- `id`: …
- `post`: FK → Post
- `user`: FK → User
- `reply_to`: FK → Comment (opcional)
- `texto`: …
Constraints adicionais:
- Herda de `TimeStampedModel`

### Feed.Reacao
Descrição: Reação em post.
Campos:
- `id`: …
- `post`: FK → Post
- `user`: FK → User
- `vote`: `like` | `share`
Constraints adicionais:
- Herda de `TimeStampedModel`

### Feed.PostView
Descrição: Registro de visualização.
Campos:
- `id`: …
- `post`: FK → Post
- `user`: FK → User
- `opened_at`: …
- `closed_at`: …
Constraints adicionais:
- Herda de `TimeStampedModel`

### Feed.FeedPluginConfig
Descrição: Configuração de plugin de feed.
Campos:
- `id`: …
- `organizacao`: FK → Organizacao
- `module_path`: string
- `frequency`: int
Constraints adicionais:
- Herda de `TimeStampedModel`

## 8. Critérios de Aceite (Gherkin)

```gherkin
Feature: Denúncia e moderação de post
  Scenario: Post atinge limite de denúncias
    Given um post existente
    And usuários denunciam o post até atingir o limite
    When o limite de denúncias é alcançado
    Then o status do post passa para “pendente”
    And o motivo registra “Limite de denúncias atingido”

Feature: Curtida e notificação
  Scenario: Curtir um post
    Given um usuário visualiza um post
    When ele clica em curtir
    Then uma curtida é registrada
    And uma notificação “feed_like” é enviada ao autor

Feature: Moderação manual
  Scenario: Moderador aprova post pendente
    Given um post em status pendente
    When o moderador aprova o post
    Then o status passa a “aprovado”
    And o autor recebe uma notificação “feed_post_moderated” com status
```

## 9. Dependências e Integrações

- **Storage (S3)** – armazenamento de imagens, PDFs e vídeos.
- **App Accounts** – autenticação e contexto do usuário.
- **App Organizações**, **Núcleos**, **Eventos** – validação do escopo de publicação.
- **Celery** – processamento de uploads, notificações e moderação assíncrona.
- **App Notificações** – envio de notificações para usuários.
- **Search Engine** – índices full-text para PostgreSQL e fallback para outras bases.
- **Prometheus/Grafana** – coleta de métricas de posts criados, notificações enviadas e latência de notificações.
- **Sentry** – monitoramento de falhas em tasks e uploads.

## Anexos e Referências
...

## Changelog
- 1.1.0 — 2025-08-13 — Normalização estrutural.

