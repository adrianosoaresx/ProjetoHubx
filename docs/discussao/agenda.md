# Integração com Agenda

Ações de agendamento estão atrás da flag `FEATURE_DISCUSSAO_AGENDA` (desligada por padrão).

Com a flag ativada, é possível criar um evento na Agenda a partir de um tópico via:

```
POST /api/discussao/topicos/<id>/agendar/
```

Apenas o autor do tópico ou administradores podem executar a ação. Um evento mínimo é criado e
os participantes do tópico recebem notificação assincronamente.

Quando a flag está desligada ou o usuário não possui permissão, a API responde `403`.
