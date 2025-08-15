# Nome do Aplicativo: configuracoes

## O que este app faz (em palavras simples)
- Permite ajustar preferências pessoais de notificações, idioma e aparência.
- Envia resumos diários ou semanais por e-mail ou WhatsApp conforme sua escolha.

## Para quem é
- Usuários autenticados que desejam personalizar como recebem avisos e como a interface aparece.

## Como usar (passo a passo rápido)
1. Faça login e acesse **Menu → Configurações**.
2. Use as abas para navegar entre Informações, Segurança, Redes e **Preferências**.
3. Na aba **Preferências**, marque ou desmarque canais (e-mail, WhatsApp, push) e escolha a frequência.
4. Defina idioma e tema desejados e clique em **Salvar Alterações**.
5. Para testar notificações, chame `/api/configuracoes/testar/` informando o canal.

## Principais telas e onde encontrar
- **Configurações**: `/configuracoes/` – reúne todas as abas citadas.
- **API de Preferências**: `/api/configuracoes/configuracoes-conta/` para recuperar ou atualizar via API.

## O que você precisa saber
- É necessário estar logado para acessar as configurações.
- Notificações por push ainda não estão disponíveis via API.
- Configurações específicas por organização, núcleo ou evento ainda não podem ser criadas pela interface.

## Suporte
- Contato/Canal: suporte@hubx.space
