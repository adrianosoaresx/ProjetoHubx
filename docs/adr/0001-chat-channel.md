# 0001 - Redesign do módulo de chat

## Contexto
O antigo modelo `ChatConversation` não suportava múltiplos contextos nem
operações em tempo real com moderação.

## Decisão
- Substituição por `ChatChannel` com campos `contexto_tipo` e `contexto_id`.
- Uso de Django Channels para comunicação WebSocket.
- API REST alinhada aos serviços e tasks de exportação.

## Consequências
- Necessidade de migração dos dados existentes.
- Simplificação das permissões e expansão da moderação.
