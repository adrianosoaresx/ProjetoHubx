from __future__ import annotations

from enum import Enum


class TipoUsuario(Enum):
    ROOT = "root"
    ADMIN = "admin"
    COORDENADOR = "coordenador"
    NUCLEADO = "nucleado"
    ASSOCIADO = "associado"
    CONVIDADO = "convidado"

    @classmethod
    def choices(cls) -> list[tuple[str, str]]:
        return [(member.value, member.name) for member in cls]
