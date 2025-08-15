# Nome do Aplicativo: accounts

## O que este app faz (em palavras simples)
- Gerencia contas de usuário: cadastro, login, perfil, recuperação de senha e exclusão.
- Permite ativar segurança extra com códigos de verificação (2FA).
- Guarda conexões entre usuários e arquivos de mídia pessoais.

## Para quem é
- Pessoas que usam o Hubx e precisam criar ou administrar sua conta.

## Como usar (passo a passo rápido)
1. Acesse `/accounts/login/` para entrar com seu e-mail e senha.
2. Caso ainda não tenha conta, clique em **Cadastre-se gratuitamente** e siga as etapas guiadas pelo token de convite.
3. Após o login, vá em **Perfil → Informações Pessoais** para atualizar seus dados e fotos.
4. Para habilitar 2FA, navegue em **Perfil → Segurança → 2FA** e siga as instruções do QR code.
5. Em **Perfil → Mídias** você pode enviar, editar ou remover arquivos com tags.
6. Para sair, use o link **Sair** ou `/accounts/logout/`.

## Principais telas e onde encontrar
- **Login**: `/accounts/login/`
- **Cadastro multietapas**: `/accounts/onboarding/` e etapas subsequentes
- **Perfil**: `/accounts/perfil/` com abas de informações, redes sociais, segurança e mídias
- **Recuperação de senha**: `/accounts/password_reset/`

## O que você precisa saber
- Confirme seu e-mail dentro de 24h para ativar a conta.
- Após três erros de login seguidos a conta fica bloqueada por 15 minutos.
- Contas excluídas podem ser recuperadas em até 30 dias.

## Suporte
- Contato/Canal: suporte@hubx.space
