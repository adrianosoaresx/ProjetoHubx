# Feed API

Endpoints under `/api/feed/` provide CRUD access to posts, comments, reações e moderações.

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
`image_url`, `pdf_url` and `video_url` fields. Sempre que um link for detectado no
conteúdo, o payload retorna também um objeto `link_preview` somente leitura com as
chaves `url`, `title`, `description`, `image` e `site_name` contendo os metadados
armazenados.

Exemplo de listagem filtrada:

```bash
curl /api/feed/posts/?tags=django&date_from=2025-01-01
```

Cada post pode conter **apenas um** tipo de mídia (imagem, vídeo ou PDF).
Uploads são enviados ao S3 com tentativas de reenvio em caso de falha. Em
ambientes de testes `CELERY_TASK_ALWAYS_EAGER=True` o envio ocorre
sincronamente chamando diretamente o serviço interno. Em produção a
operação é enfileirada via Celery e uma chave temporária é retornada
imediatamente; o processamento assíncrono atualiza o registro quando
finalizado.

Posts contendo palavras proibidas são marcados para moderação e só aparecem
após aprovação.

### Link preview persistido

O endpoint `GET /api/feed/posts/link-preview/` continua disponível para gerar
pré-visualizações em tempo real, porém as respostas dos posts passam a incluir o
campo `link_preview` já persistido no modelo. Clientes podem exibir cartões sem
realizar chamadas adicionais sempre que o campo não estiver vazio.

### Busca

O parâmetro `q` aceita múltiplos termos. Os termos separados por espaço usam o
operador lógico **AND**. Para buscas com **OR**, separe termos com `|`. Em
ambientes PostgreSQL a busca usa `SearchVector` com rank e ordenação por
relevância.

### Notificações

Após a criação de um post, uma tarefa Celery envia notificações para usuários da
mesma organização. Métricas Prometheus acompanham a quantidade de posts e
notificações enviadas.

## Comments

`/api/feed/comments/` permite criar e remover comentários em posts. Autenticação é
obrigatória para todos os endpoints.

## Reações

Reações permitem registrar `like` ou `share` em posts através dos endpoints:

- `POST /api/feed/posts/{post_id}/reacoes/` com corpo `{ "vote": "like" | "share" }`
- `GET /api/feed/posts/{post_id}/reacoes/` retorna contagem agregada e reação do usuário
- Repetir o `POST` com o mesmo `vote` remove a reação existente

Para curtir um post utilize o endpoint acima com `vote="like"`. O antigo
`/api/feed/likes/` foi removido.

## Visualizações

Ao abrir uma página de post a interface chama automaticamente:

- `POST /api/feed/posts/{post_id}/views/open/`
- `POST /api/feed/posts/{post_id}/views/close/`

Os dados alimentam métricas Prometheus de visualizações e tempo de leitura.

Integração com S3 requer credenciais com permissão de `s3:PutObject` e
`s3:GetObject` no *bucket* configurado em `AWS_STORAGE_BUCKET_NAME`.

### Populando prévias de links existentes

Para preencher o novo campo em posts antigos execute:

```bash
python manage.py populate_post_link_previews --limit 200
```

Use `--dry-run` para conferir os registros que seriam alterados e `--force` caso
precise recalcular prévias já armazenadas.

## Plugins

Organizações podem estender o feed registrando classes que implementem o
protocolo `FeedPlugin`. Cada plugin pode injetar itens personalizados no feed
de acordo com o usuário atual. As configurações são armazenadas em
`FeedPluginConfig` e carregadas dinamicamente em tempo de execução.

Veja mais detalhes em [`docs/feed_plugins.md`](../docs/feed_plugins.md).

## Rate limiting

Requisições aos endpoints de posts são limitadas por usuário. Os limites
podem ser ajustados através das configurações `FEED_RATE_LIMIT_POST` e
`FEED_RATE_LIMIT_READ`.
