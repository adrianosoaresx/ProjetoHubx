from __future__ import annotations

from typing import Iterable

from django.contrib.auth import get_user_model

from .models import Nucleo, ParticipacaoNucleo

User = get_user_model()


def criar_participacoes_membros(nucleo: Nucleo, membros: Iterable[User]) -> list[ParticipacaoNucleo]:
    """Cria participações aprovadas para a lista de membros fornecida."""
    participacoes: list[ParticipacaoNucleo] = []
    for user in membros:
        part, _ = ParticipacaoNucleo.objects.get_or_create(nucleo=nucleo, user=user)
        part.status = "ativo"
        part.save(update_fields=["status"])
        participacoes.append(part)
    return participacoes

