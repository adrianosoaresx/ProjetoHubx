# Nome do Aplicativo: tokens

## O que este app faz (em palavras simples)
- Gera convites para novos usuários e tokens de API para integrações.
- Registra códigos de autenticação temporários e permite ativar a verificação em duas etapas (2FA).

## Para quem é
- Administradores que precisam convidar pessoas ou gerenciar acessos.
- Usuários que desejam integrar sistemas externos via API ou ativar 2FA.

## Como usar (passo a passo rápido)
1. Acesse o menu **Tokens** após fazer login.
2. Para gerar um convite, vá em **Gerar Token** e escolha o tipo de usuário.
3. Para validar um convite recebido, abra **Validar Token** e informe o código.
4. Para criar um token de API, use `POST /api/api-tokens/` com `scope` e `expires_in` (opcional).
5. Para ativar 2FA, acesse **Ativar 2FA** e siga o código exibido no aplicativo autenticador.

## Principais telas e onde encontrar
- **Gerar Token:** `/tokens/gerar-token/`
- **Validar Token:** `/tokens/validar-token/`
- **Ativar 2FA:** `/tokens/ativar-2fa/`
- **Gerar Código de Autenticação:** `/tokens/gerar-codigo/`

## O que você precisa saber
- Permissões necessárias: apenas staff pode gerar convites; revogar tokens exige perfil de administrador.
- Limitações atuais: não há rotação automática de tokens nem restrição por IP.
- Dúvidas comuns:
  - **Quantos convites posso gerar?** Até cinco por dia.
  - **Posso restringir por IP?** Ainda não, use filtros externos.
  - **Como revogar um token?** Via `/api/tokens/<codigo>/revogar/` ou removendo o token de API criado.

## Suporte
- Canal: suporte@hubx.space
