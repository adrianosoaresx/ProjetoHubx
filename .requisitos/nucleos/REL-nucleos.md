# App Núcleos

O módulo Núcleos organiza grupos temáticos dentro de uma mesma organização.
Nele é possível criar núcleos com identidade visual, controlar quem participa
e acompanhar métricas de engajamento.

## Funcionalidades principais

- criar, editar e remover núcleos com avatar, capa e valor de mensalidade;
- listar núcleos da organização com paginação e cache;
- solicitar entrada, aprovar, recusar, suspender ou reativar membros;
- gerar convites com limite diário e aceitar convites por token;
- definir coordenadores suplentes com período de vigência;
- exportar membros em CSV ou XLS e gerar relatório geral em CSV ou PDF;
- publicar posts no feed do núcleo e consultar métricas agregadas.

## Fluxos do usuário

### Criar núcleo
1. Acesse o endpoint ou interface de criação.
2. Informe nome, descrição, avatar e capa.
3. Receba confirmação de criação.

### Solicitar participação
1. Acesse o núcleo desejado e use a opção **Solicitar**.
2. Aguarde aprovação de um admin ou coordenador.

### Aprovar ou suspender membro
1. Admin ou coordenador abre a lista de membros pendentes ou ativos.
2. Usa a ação **aprovar**, **recusar**, **suspender** ou **reativar**.

### Gerar convite
1. Admin solicita criação de convite informando e‑mail e papel.
2. Sistema envia token; o convidado acessa `/api/nucleos/aceitar-convite/?token=...`.

### Designar suplente
1. Admin ou coordenador escolhe membro ativo e define período.
2. Suplente recebe notificação válida apenas nas datas informadas.

### Exportar membros
1. Admin ou coordenador requisita exportação.
2. Baixe arquivo CSV ou XLS com dados dos participantes.

## Endpoints e usos comuns

- `POST /api/nucleos/` cria núcleo.
- `GET /api/nucleos/?organizacao=<id>` lista núcleos da organização.
- `POST /api/nucleos/<id>/solicitar/` cria solicitação de participação.
- `POST /api/nucleos/<id>/membros/<user_id>/aprovar` aprova membro.
- `POST /api/nucleos/<id>/membros/<user_id>/suspender` suspende membro.
- `POST /api/nucleos/<id>/convites/` gera convite para e‑mail.
- `GET /api/nucleos/aceitar-convite/?token=<token>` aceita convite.
- `POST /api/nucleos/<id>/suplentes/` cria suplente.
- `GET /api/nucleos/<id>/membros/exportar?formato=csv` exporta membros.
- `GET /api/nucleos/<id>/metrics/` retorna métricas básicas.

## Modelos e campos

- **Núcleo**: id, organizacao, nome, slug, descricao, avatar, cover, ativo, mensalidade.
- **ParticipacaoNucleo**: id, user, nucleo, papel, status, status_suspensao, data_suspensao,
  data_solicitacao, data_decisao, decidido_por, justificativa.
- **CoordenadorSuplente**: id, nucleo, usuario, periodo_inicio, periodo_fim.
- **ConviteNucleo**: id, token, token_obj, email, papel, limite_uso_diario,
  data_expiracao, usado_em, criado_em, nucleo.

## Permissões por papel

- **root/admin**: todas as ações, inclusive convites, relatórios e suspensão.
- **coordenador**: aprova/recusa solicitações, suspende/reativa membros, cria suplentes.
- **associado**: solicita participação, aceita convite, publica se ativo.
- **convidado**: apenas leitura pública quando disponível.

## Integrações e limitações

- Usa Storage S3 para avatar e capa.
- Integra com Tokens para convites, Feed para posts e Financeiro para cobranças.
- Notificações enviadas por Celery.
- Métricas exportadas via Prometheus.
- Cache de listas e métricas expira em cinco minutos.
- Convites expiram em sete dias e seguem limite diário por emissor.

## FAQ

- **Como entro em um núcleo?** Solicite participação ou use o link de convite.
- **Posso remover um membro definitivamente?** Hoje a remoção ocorre via status
  inativo; política de exclusão definitiva está em discussão.
- **Convites têm validade?** Sim, expiram após sete dias ou quando revogados.

