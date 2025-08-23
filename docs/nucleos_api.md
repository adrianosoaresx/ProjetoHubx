# API de Núcleos

Endpoints introduzidos na Sprint 2 para convites, suspensão de membros e posts no feed.

O modelo `Nucleo` possui o campo booleano `ativo` (padrão `true`), permitindo ativar ou desativar núcleos via API ou interface.

## Convites
- `POST /api/nucleos/{id}/convites/` — gera um convite para o núcleo, respeitando o limite diário por usuário.
- `DELETE /api/nucleos/{id}/convites/{convite_id}/` — revoga o convite informado, marcando-o como expirado.

## Suspensão de Membros
- `POST /api/nucleos/{id}/membros/{user_id}/suspender/` — suspende o participante ativo.
- `POST /api/nucleos/{id}/membros/{user_id}/reativar/` — reativa o participante suspenso.
- `GET /api/nucleos/{id}/membro-status/` — retorna `{papel, ativo, suspenso}` para o usuário autenticado.

## Participações
- `POST /api/nucleos/{id}/solicitar/` — solicita participação no núcleo para o usuário autenticado. Retorna erro se já houver solicitação ou se o usuário já for membro.

## Feed do Núcleo
- `POST /api/nucleos/{id}/posts/` — cria um post no feed do núcleo para membros ativos não suspensos.
