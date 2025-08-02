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

## Comments and Likes

`/api/feed/comments/` and `/api/feed/likes/` allow creating and removing comments and likes
for posts. Authentication is required for all endpoints.

Integração com S3 requer credenciais com permissão de `s3:PutObject` e
`s3:GetObject` no *bucket* configurado em `AWS_STORAGE_BUCKET_NAME`.
