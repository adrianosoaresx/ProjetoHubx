# Chat API

Endpoints REST para gerenciamento de canais e mensagens. Requer autenticação via token JWT ou sessão.

## Exemplo de criação de canal

```http
POST /api/chat/channels/
Content-Type: application/json

{
  "contexto_tipo": "privado",
  "titulo": "Bate-papo"
}
```

## Listar mensagens de um canal

```http
GET /api/chat/channels/<id>/messages/
Authorization: Bearer <token>
```

Parâmetros opcionais:

- `desde=<timestamp>` – mensagens a partir de uma data/hora.
- `ate=<timestamp>` – mensagens até uma data/hora.

## Permissões

- Apenas participantes conseguem acessar um canal.
- Somente administradores ou proprietários podem adicionar/remover participantes.
- Canais de núcleo, evento ou organização exigem privilégios de staff para criação.

