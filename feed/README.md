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

## Comments and Likes

`/api/feed/comments/` and `/api/feed/likes/` allow creating and removing comments and likes
for posts. Authentication is required for all endpoints.
