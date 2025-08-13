### Funcionalidades
- Gerar tokens de convite para novos usuários, com expiração e uso único.
- Emitir tokens de API com escopo "read", "write" ou "admin" e expiração opcional.
- Registrar logs de geração, validação, uso e revogação com IP e user agent.
- Revogar tokens manualmente e consultar histórico de acesso.
- Suporte a códigos de autenticação e dispositivos TOTP para 2FA.

### Fluxos principais
- **Emitir token de convite**
  1. Autentique-se como usuário autorizado.
  2. Envie `POST /api/tokens/` com `tipo_destino`, `organizacao` e `nucleos`.
  3. Receba `HTTP 201` com dados do token.
  ```bash
  curl -X POST -H 'Authorization: Bearer <jwt>' \
       -H 'Content-Type: application/json' \
       -d '{"tipo_destino":"associado"}' \
       https://api.exemplo.com/api/tokens/
  ```
- **Renovar ou rotacionar token**
  - Não há endpoint dedicado; gere um novo token e revogue o antigo.
- **Revogar token**
  ```bash
  curl -X POST -H 'Authorization: Bearer <jwt>' \
       https://api.exemplo.com/api/tokens/<codigo>/revogar/
  ```
- **Listar tokens da conta**
  ```bash
  curl -H 'Authorization: Bearer <jwt>' https://api.exemplo.com/api/api-tokens/
  ```
- **Configurar escopos de API**
  - Informe o campo `scope` ao criar o token (`read`, `write` ou `admin`).
- **Associar a device**
  - Tokens não vinculam devices; para 2FA utilize `POST /tokens/ativar-2fa/` no site.
- **Aplicar IP allow/deny**
  - Recurso indisponível; filtros de IP devem ser aplicados externamente.
- **Consultar auditoria**
  ```bash
  curl -H 'Authorization: Bearer <jwt>' https://api.exemplo.com/api/tokens/<id>/logs/
  ```

### Endpoints principais
- `POST /api/tokens/` – cria token de convite.
- `GET /api/tokens/validate/?codigo=<c>` – valida token.
- `POST /api/tokens/<id>/use/` – consome token.
- `POST /api/tokens/<codigo>/revogar/` – revoga token.
- `GET /api/tokens/<id>/logs/` – retorna auditoria.
- `GET/POST /api/api-tokens/` – lista ou cria tokens de API.
- `DELETE /api/api-tokens/<id>/` – revoga token de API.

### Permissões por papel
- **root**: acesso total a tokens e logs.
- **admin**: pode criar convites, revogar tokens e gerenciar escopos de API.
- **gestor**: pode emitir convites; não revoga tokens alheios.
- **usuário final**: pode usar convites e gerar tokens de API com escopos "read" ou "write".

### Boas práticas
- Use expiração curta para tokens de acesso.
- Restrinja tokens de refresh a ambientes confiáveis e rotacione após cada uso.
- Aplique princípio do menor privilégio ao definir escopos.
- Revogue tokens comprometidos e gere novos imediatamente.
- Nunca registre segredos ou tokens em logs.

### FAQ
- **Quantos convites posso gerar por dia?** Até cinco por usuário.
- **Posso renovar um token de API?** Gere um novo e delete o antigo.
- **Existe limite de uso por IP?** Ainda não; use controles externos.
- **Como ativar 2FA?** Acesse `/tokens/ativar-2fa/` e siga as instruções com aplicativo TOTP.
- **Posso restringir token a um dispositivo específico?** Não há suporte nativo.
