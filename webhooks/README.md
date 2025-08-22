# Webhooks

Este módulo gerencia inscrições e eventos de webhook.

## Retenção de eventos

Eventos entregues são mantidos por `WEBHOOK_EVENT_RETENTION_DAYS` dias (padrão 30).
A tarefa Celery `remover_eventos_antigos` roda diariamente à meia-noite via `celery beat`
removendo eventos entregues mais antigos que esse limite.

