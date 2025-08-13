# Descrição do App Notificações

## Objetivo
Centralizar o envio de mensagens transacionais (cobranças, avisos, confirmações) com templates, preferências, filas assíncronas, métricas e entrega **in‑app** em tempo real.

## Funcionalidades
- Cadastro e edição de **templates** com código único, assunto, corpo, canal e ativo.
- Serviço interno `enviar_para_usuario(codigo, user_id, contexto)` com renderização.
- Envio **assíncrono** via Celery, com **até 3 retentativas** e Sentry.
- **Logs** por usuário, template, canal, status (pendente/enviada/falha/lida) e erro.
- **Push** por canais configurados: E‑mail, WhatsApp, Push (OneSignal e WebPush).
- **In‑app** via WebSocket (`ws/notificacoes/`) com grupos por usuário.
- **Preferências** do usuário respeitadas, incluindo **frequência** (imediata/diária/semanal).
- **Resumo** diário/semanal: agrega mensagens pendentes e registra em `HistoricoNotificacao`.
- **Métricas** Prometheus: enviados/falhas por canal, total de templates e duração de tasks.
- **Admin** com exportação CSV de logs e bloqueio de exclusão de template em uso.
- **API REST** para templates, logs, push/subscriptions e disparo autenticado.

## Fluxos principais
- **Disparo individual**: módulo chama o serviço/endpoint; aplica template e preferências; agenda task; atualiza log ao finalizar.
- **Disparo em massa**: módulo externo itera destinatários e chama o serviço; Celery processa por canal e registra resultados.
- **Leitura in‑app**: cliente abre `ws/notificacoes/`; ao receber evento, exibe resumo e, opcionalmente, marca como **lida** via `PATCH /logs/<built-in function id>`.
- **Resumo diário/semanal**: job seleciona pendentes conforme preferências de frequência e envia uma mensagem agregada por canal; registra em `HistoricoNotificacao`.
- **Gestão de templates**: criar/editar/desativar; exclusão só quando **não há logs** associados.

## Endpoints REST (base `/api/notificacoes/`)
- `POST enviar/` — disparo interno; requer `notificacoes.can_send_notifications`.
- `GET/POST/PUT/PATCH/DELETE templates/` — CRUD (admin).
- `GET logs/` — leitura paginada; `PATCH logs/<built-in function id>` para marcar **lida**.
- `GET/POST/DELETE push/subscriptions/` — gerencia inscrições Web Push do usuário.

## WebSocket
- URL: `ws/notificacoes/`.
- Autenticado; associação ao grupo `notificacoes_<user_id>`.
- Evento `notification_message` com payload JSON.

## Integrações
- **Email** (Django Email Backend).
- **WhatsApp** (Twilio).
- **Push** (OneSignal e WebPush/pywebpush).
- **Preferências** via `configuracoes.services.get_user_preferences`.
- **Observabilidade**: Prometheus, Sentry, logs estruturados.

## Configuração (variáveis esperadas)
- `NOTIFICATIONS_EMAIL_API_URL`, `NOTIFICATIONS_EMAIL_API_KEY`.
- `NOTIFICATIONS_PUSH_API_KEY`.
- `NOTIFICATIONS_WHATSAPP_API_URL`, `NOTIFICATIONS_WHATSAPP_API_KEY`.
- `VAPID_PRIVATE_KEY`, `VAPID_CLAIM_SUB` (para WebPush).
- `DEFAULT_FROM_EMAIL`, `ONESIGNAL_APP_ID`, `ONESIGNAL_API_KEY`, `TWILIO_*` quando aplicável.

## Permissões
- Disparo interno: `notificacoes.can_send_notifications`.
- Gestão de templates: admin.
- Logs: leitura autenticada; leitura in‑app por WebSocket para o próprio usuário.

## Observações
- **Imutabilidade de logs** recomendada via admin read‑only e política de retenção.
- **Soft delete** não implementado no app; usar quando houver necessidade de retenção com exclusão lógica.
