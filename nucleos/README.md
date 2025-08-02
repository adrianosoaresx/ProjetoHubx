# Núcleos

Views principais:

- `nucleos:list` – lista núcleos ativos com busca por nome ou *slug*.
- `nucleos:create` – criação de núcleo vinculado à organização do usuário.
- `nucleos:update` – edição de dados básicos do núcleo.
- `nucleos:toggle_active` – inativa ou reativa um núcleo.
- `nucleos:exportar_membros` – exporta membros em CSV.

Fluxo de participação:

1. Usuário solicita participação (`participacao_solicitar`).
2. Coordenadores/Admins aprovam ou recusam (`participacao_decidir`).
3. Status possíveis: `pendente`, `aprovado`, `recusado` (um usuário por núcleo).

Permissões:

- Administradores e superadmins podem criar/editar/excluir.
- Coordenadores podem gerenciar membros e inativar núcleos.
- Todas as views exigem autenticação.

