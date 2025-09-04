# Núcleos

Views principais:

- `nucleos:list` – lista núcleos ativos com busca por nome.
- `nucleos:meus` – exibe apenas os núcleos dos quais o usuário participa; indisponível para administradores.
- `nucleos:create` – criação de núcleo vinculado à organização do usuário.
- `nucleos:update` – edição de dados básicos do núcleo.
- `nucleos:toggle_active` – inativa ou reativa um núcleo.
- `nucleos_api:nucleo-metrics` – retorna métricas do núcleo.

Fluxo de participação:

1. Usuário solicita participação (`participacao_solicitar`).
2. Coordenadores/Admins aprovam ou recusam (`participacao_decidir`).
3. Status possíveis: `pendente`, `aprovado`, `recusado` (um usuário por núcleo).

Permissões:

- Administradores e superadmins podem criar/editar/excluir.
- Coordenadores podem gerenciar membros e inativar núcleos.
- Todas as views exigem autenticação.

Modelos:

- `Nucleo`, `ParticipacaoNucleo` e `CoordenadorSuplente` utilizam o mixin `TimeStampedModel`.
- `Nucleo` também herda de `SoftDeleteModel`, permitindo exclusão lógica via `soft_delete()`.
- Participações aprovadas podem ser acessadas pelo atributo `nucleo.membros` e coordenadores por `nucleo.coordenadores`.
> O endpoint `nucleos_api:nucleo-relatorio` foi removido.
