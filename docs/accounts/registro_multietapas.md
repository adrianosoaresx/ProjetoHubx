# Registro multietapas via convite

Este fluxo guia o novo usuário convidado em etapas sequenciais. A pré‑condição é
possuir um **token de convite válido** (`TokenAcesso`) que define o tipo de
usuário e, opcionalmente, o núcleo de destino.

## Etapas

1. **Nome de usuário** – identificação única. Validar caracteres permitidos.
2. **Nome completo** – texto livre obrigatório.
3. **CPF** – deve ser válido e único (`RegexValidator`).
4. **E‑mail** – usado para comunicação e confirmação. Deve ser único.
5. **Senha** – validação de força com `validate_password`.
6. **Foto** – opcional; arquivo temporário salvo em `storage`.
7. **Aceite de termos** – finaliza cadastro, cria usuário inativo e envia
   e‑mail de confirmação.

## Validações e mensagens

| Etapa | Validação | Erro/Sucesso |
|-------|-----------|--------------|
| Token | estado `NOVO`, não expirado | `Token inválido` / segue fluxo |
| CPF   | formato `000.000.000-00`, único | `CPF inválido` |
| E‑mail| formato válido e único | `E‑mail já cadastrado` |
| Senha | `validate_password` | mensagens do validador |
| Termos| checkbox obrigatório | `Você deve aceitar os termos` |

Após o aceite, o usuário é criado com `is_active=False` e um `AccountToken` de
confirmação (24 h) é enviado por e‑mail. Mensagens de feedback utilizam
`django.contrib.messages` e novos textos são marcados com `gettext`.

### Acessibilidade

Campos críticos possuem `aria-describedby` apontando para `help_text` com
informações adicionais. Títulos das etapas utilizam headings (`<h1>`) e a ordem
dos elementos segue fluxo lógico para navegação assistida.

### Reenvio de confirmação

Após concluir o cadastro, o usuário pode solicitar novo e‑mail de confirmação.
Tokens antigos são marcados como usados e não podem ser reutilizados.

**Endpoint**: `POST /api/accounts/resend-confirmation/`

```json
{
  "email": "usuario@example.com"
}
```

O endpoint não exige autenticação e retorna `204 No Content` mesmo quando o e‑mail
não existir. Caso a conta já esteja ativa, é retornado `400` com a mensagem
`"Conta já ativada."`.

