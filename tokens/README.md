# Tokens de API

Este módulo fornece autenticação via **tokens de API** para integrações externas.

## Uso

### Geração

```http
POST /api/api-tokens/
{
  "scope": "read",  // read, write ou admin
  "expires_in": 30    // dias
}
```

O valor do token é retornado apenas uma vez na criação. Guarde-o com segurança.

### Autenticação

Envie o cabeçalho:

```
Authorization: Bearer <token>
```

### Revogação

```http
DELETE /api/api-tokens/<id>/
```

### Segurança

- Utilize sempre HTTPS.
- Revogue tokens comprometidos imediatamente.
- A validade máxima recomendada é de 1 ano.

