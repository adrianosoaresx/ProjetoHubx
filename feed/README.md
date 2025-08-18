# Feed API

Endpoints under `/api/feed/` provide CRUD access to posts, comments, likes and moderações.

## Posts

`/api/feed/posts/` supports the standard REST actions. Query parameters for listing:

- `tipo_feed`: `global`, `usuario`, `nucleo` or `evento`
- `organizacao`: UUID of the organização
- `nucleo`: id of the núcleo
- `evento`: id of the evento
- `tags`: comma separated tag ids or names
- `date_from` / `date_to`: ISO dates limiting creation date
- `q`: full text search in content or tag names
- `page`: pagination page

Listings are cached for 60 seconds per usuário e parâmetros de busca. Qualquer criação,
edição ou remoção de post limpa o cache automaticamente.

Deleting a post performs a *soft delete* (`deleted=True`). Media URLs are exposed via
`image_url`, `pdf_url` and `video_url` fields.

Exemplo de listagem filtrada:

```bash
curl /api/feed/posts/?tags=django&date_from=2025-01-01
```

Cada post pode conter **apenas um** tipo de mídia (imagem, vídeo ou PDF).
Uploads são enviados ao S3 com tentativas de reenvio em caso de falha.

Posts contendo palavras proibidas são marcados para moderação e só aparecem
após aprovação.

### Busca

O parâmetro `q` aceita múltiplos termos. Os termos separados por espaço usam o
operador lógico **AND**. Para buscas com **OR**, separe termos com `|`. Em
ambientes PostgreSQL a busca usa `SearchVector` com rank e ordenação por
relevância.

### Notificações

Após a criação de um post, uma tarefa Celery envia notificações para usuários da
mesma organização. Métricas Prometheus acompanham a quantidade de posts e
notificações enviadas.

## Comments and Likes

`/api/feed/comments/` and `/api/feed/likes/` allow creating and removing comments and likes
for posts. Authentication is required for all endpoints.

## Reações

Reações permitem registrar `like` ou `share` em posts através dos endpoints:

- `POST /api/feed/posts/{post_id}/reacoes/` com corpo `{ "vote": "like" | "share" }`
- `GET /api/feed/posts/{post_id}/reacoes/` retorna contagem agregada e reação do usuário
- `DELETE /api/feed/posts/{post_id}/reacoes/{vote}/` remove a reação do usuário

## Visualizações

Ao abrir uma página de post a interface chama automaticamente:

- `POST /api/feed/posts/{post_id}/views/open/`
- `POST /api/feed/posts/{post_id}/views/close/`

Os dados alimentam métricas Prometheus de visualizações e tempo de leitura.

Integração com S3 requer credenciais com permissão de `s3:PutObject` e
`s3:GetObject` no *bucket* configurado em `AWS_STORAGE_BUCKET_NAME`.

## Plugins

Organizações podem estender o feed registrando classes que implementem o
protocolo `FeedPlugin`. Cada plugin pode injetar itens personalizados no feed
de acordo com o usuário atual. As configurações são armazenadas em
`FeedPluginConfig` e carregadas dinamicamente em tempo de execução.

Veja mais detalhes em [`docs/feed_plugins.md`](../docs/feed_plugins.md).

## Rate limiting

Requisições aos endpoints de posts são limitadas por usuário. Os limites
podem ser ajustados através das configurações `FEED_RATE_LIMIT_POST` e
`FEED_RATE_LIMIT_READ`. Cada organização possui ainda um campo
`rate_limit_multiplier` que permite multiplicar esses valores para usuários
ligados a ela.
