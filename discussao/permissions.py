from __future__ import annotations

from accounts.models import UserType

# Mapping of user types to allowed publico_alvo values for TopicoDiscussao
PUBLICO_ALVO_PERMISSOES = {
    UserType.ROOT: {0, 1, 3, 4},
    UserType.ADMIN: {0, 1, 3, 4},
    UserType.FINANCEIRO: {0, 1, 3, 4},
    UserType.COORDENADOR: {0, 1, 3},
    UserType.NUCLEADO: {0, 1},
    UserType.ASSOCIADO: {0, 4},
    UserType.CONVIDADO: {0},
}


def publicos_permitidos(user_type: str) -> set[int]:
    """Retorna conjunto de valores de publico_alvo permitidos para o tipo de usuário."""
    try:
        tipo = UserType(user_type)
    except ValueError:
        return {0}
    return PUBLICO_ALVO_PERMISSOES.get(tipo, {0})
