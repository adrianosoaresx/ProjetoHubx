# AUDIT-NOTIFICACOES-001

## Resumo
Auditoria do módulo **Notificações** confrontando requisitos da especificação `REQ-NOTIFICACOES-001` com o código existente.

## Comparação de Requisitos

| Requisito | Situação | Observações |
|-----------|----------|-------------|
| RF‑01 – Cadastro de Modelos | Parcial | Falta campo `ativo`; exclusão sugere desativação. |
| RF‑02 – Preferências por Usuário | Não atendido | Não há `UserNotificationPreference`. |
| RF‑03 – Disparo de Notificações | Parcial | Falta log de falha quando todos os canais desabilitados. |
| RF‑04 – Envio Assíncrono | Atendido | Celery com retentativas e métricas. |
| RF‑05 – Registro de Logs | Parcial | Ausência de `data_leitura`. |
| RF‑06 – Métricas | Atendido | Counters e gauge presentes. |
| RF‑07 – Integração com outros módulos | Atendido | Serviço `enviar_para_usuario`. |
| RF‑08 – WebSocket | Atendido | Consumer `NotificationConsumer`. |
| RF‑09 – Marcar LIDA | Não atendido | Endpoint não grava `data_leitura`. |
| RF‑10 – PushSubscription | Parcial | Não há campo `ativo`; remoção direta. |
| RF‑11 – Resumos Diário/Semanal | Parcial | `HistoricoNotificacao` sem `frequencia` e `data_referencia`. |
| RF‑12 – Permissão Endpoint | Atendido | `CanSendNotifications` aplicado. |

## Riscos e Bugs
- Logs de notificações não registram leitura.
- Ausência de modelo de preferências pode gerar envios indesejados.
- Templates não podem ser ativados/desativados formalmente.
- Histórico de resumos carece de metadados para auditoria.

## Recomendações
1. Implementar campos e modelos faltantes conforme issues listadas.
2. Revisar fluxo de falhas para garantir rastreabilidade.
3. Ampliar cobertura de testes após as alterações.
