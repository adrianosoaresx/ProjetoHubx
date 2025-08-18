from __future__ import annotations

from typing import Iterable

from django.conf import settings

from ..models import TopicoDiscussao


def criar_reuniao(
    topico: TopicoDiscussao,
    data_inicio,
    data_fim,
    participantes: Iterable,
):
    """Dispara a criação de uma reunião na Agenda quando habilitado."""

    if not getattr(settings, "DISCUSSAO_AGENDA_BRIDGE_ENABLED", False):
        return None

    from agenda import services as agenda_services

    return agenda_services.criar_reuniao(
        topico=topico,
        data_inicio=data_inicio,
        data_fim=data_fim,
        participantes=participantes,
    )

