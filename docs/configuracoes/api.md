# API de Configurações

Endpoints principais:

- `GET /api/configuracoes/configuracoes-conta/` – obtém preferências globais do usuário.
- `PATCH /api/configuracoes/configuracoes-conta/` – atualiza preferências globais.
- `GET /api/configuracoes/contextuais/` – lista configurações por escopo.
- `POST /api/configuracoes/contextuais/` – cria nova configuração contextual.
- `PUT/PATCH/DELETE /api/configuracoes/contextuais/<id>/` – gerencia configuração contextual existente.
- `POST /api/configuracoes/testar/` – envia notificação de teste para o escopo informado.

Os campos `receber_notificacoes_push` e `frequencia_notificacoes_push` permitem habilitar o canal push
seguindo as frequências: `imediata`, `diaria` ou `semanal`.
