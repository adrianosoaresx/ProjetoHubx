# Validação de CNPJ

Endpoint para validação de CNPJ antes do cadastro/edição de empresas.

```
POST /api/empresas/validar-cnpj/
```

## Exemplo de requisição

```json
{
  "cnpj": "19131243000197"
}
```

## Exemplo de resposta

```json
{
  "cnpj_formatado": "19.131.243/0001-97",
  "valido_local": true,
  "valido_externo": true,
  "fonte": "brasilapi",
  "mensagem": ""
}
```

- `valido_externo` pode ser `null` quando o serviço externo está indisponível.
- Em caso de indisponibilidade do serviço externo, o endpoint retorna `503`.
- O endpoint é protegido por `IsAuthenticated` e utiliza throttling com o escopo `validar_cnpj`.
