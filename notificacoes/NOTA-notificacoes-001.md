# Nome do Aplicativo: notificacoes

## O que este app faz (em palavras simples)
- Centraliza o envio de e-mails, mensagens push e WhatsApp para avisos importantes.
- Guarda registros de cada notificação enviada e permite acompanhar o histórico.

## Para quem é
- Administradores e módulos internos que precisam disparar mensagens transacionais para usuários do Hubx.

## Como usar (passo a passo rápido)
1. Acesse o painel e vá em **Notificações → Templates** para criar ou editar modelos de mensagem.
2. Para disparar uma notificação manualmente, use o endpoint `POST /api/notificacoes/enviar/` informando o código do template e o usuário.
3. Os usuários recebem as mensagens pelos canais permitidos (e-mail, push ou WhatsApp) e podem vê-las em **Notificações → Histórico**.
4. O sistema atualiza os status automaticamente e exibe métricas em **Notificações → Métricas**.

## Principais telas e onde encontrar
- **Templates:** menu superior → Notificações → Templates.
- **Logs:** menu superior → Notificações → Logs.
- **Histórico:** menu superior → Notificações → Histórico.
- **Métricas:** menu superior → Notificações → Métricas.

## O que você precisa saber
- Permissões necessárias: apenas usuários autenticados podem acessar as telas; envio via API exige permissão `notificacoes.can_send_notifications`.
- Limitações atuais: o painel de métricas não exibe o total de templates cadastrados.
- Dúvidas comuns:
  - **Como marcar uma notificação como lida?** Use `PATCH /api/notificacoes/logs/<id>` com `{"status": "lida"}`.
  - **Como receber notificações no navegador?** Cadastre seu dispositivo em **/api/notificacoes/push/subscriptions/**.

## Suporte
- Contato/Canal: suporte@hubx.space
