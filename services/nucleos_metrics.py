from __future__ import annotations

from django.contrib.auth import get_user_model
from django.db.models import Count
from django.utils import timezone

from nucleos.models import ParticipacaoNucleo, CoordenadorSuplente

User = get_user_model()


def get_total_membros(nucleo_id: str) -> int:
    """Retorna o número total de membros aprovados de um núcleo."""
    return (
        ParticipacaoNucleo.objects.filter(
            nucleo_id=nucleo_id, status="aprovado", deleted=False
        ).count()
    )


def get_total_suplentes(nucleo_id: str) -> int:
    """Retorna o número de suplentes ativos do núcleo."""
    now = timezone.now()
    return (
        CoordenadorSuplente.objects.filter(
            nucleo_id=nucleo_id,
            periodo_inicio__lte=now,
            periodo_fim__gte=now,
            deleted=False,
        ).count()
    )


def get_membros_por_status(nucleo_id: str) -> dict[str, int]:
    """Retorna a contagem de participações agrupadas por status."""
    qs = (
        ParticipacaoNucleo.objects.filter(nucleo_id=nucleo_id, deleted=False)
        .values("status")
        .annotate(total=Count("id"))
    )
    return {row["status"]: row["total"] for row in qs}


def get_taxa_participacao(organizacao_id: str) -> float:
    """Retorna a taxa de participação de associados da organização em núcleos."""
    total_associados = User.objects.filter(
        organizacao_id=organizacao_id, is_associado=True, deleted=False
    ).count()
    if total_associados == 0:
        return 0.0
    participantes = (
        User.objects.filter(
            organizacao_id=organizacao_id,
            is_associado=True,
            participacoes__status="aprovado",
            participacoes__deleted=False,
        )
        .distinct()
        .count()
    )
    return round(participantes * 100 / total_associados, 2)
