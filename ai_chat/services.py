from __future__ import annotations

from datetime import datetime
import uuid
from typing import Any, Iterable

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.utils import timezone

from dashboard.services import (
    build_chart_payload,
    build_time_series_chart,
    calculate_event_status_totals,
    calculate_membership_totals,
    calculate_monthly_membros,
)
from eventos.models import Evento, InscricaoEvento
from nucleos.models import Nucleo, ParticipacaoNucleo
from organizacoes.models import Organizacao
from services import nucleos_metrics


def _serialize_datetime(value: datetime | None) -> str | None:
    """Normaliza datas para ``isoformat`` serializável."""

    if not value:
        return None
    if timezone.is_naive(value):
        return value.isoformat()
    return timezone.localtime(value).isoformat()


def get_membership_totals(organizacao_id: str) -> dict[str, Any]:
    """Retorna totais de membros por tipo e payload de gráfico para a organização informada."""

    totals = calculate_membership_totals(organizacao_id)
    return {
        "organizacao_id": str(organizacao_id),
        "totals": dict(totals),
        "chart": build_chart_payload(totals),
    }


def get_event_status_totals(organizacao_id: str) -> dict[str, Any]:
    """Retorna totais de eventos por status e payload de gráfico para a organização informada."""

    totals = calculate_event_status_totals(organizacao_id)
    return {
        "organizacao_id": str(organizacao_id),
        "totals": dict(totals),
        "chart": build_chart_payload(totals),
    }


def get_monthly_members(organizacao_id: str, *, months: int = 12, reference: datetime | None = None) -> dict[str, Any]:
    """Retorna evolução mensal de novos membros com figura Plotly serializável para a organização."""

    data_points = calculate_monthly_membros(
        organizacao_id,
        months=months,
        reference=reference,
    )
    chart = build_time_series_chart(
        data_points,
        value_field="total",
        std_field="std_dev",
        label="Novos associados",
        yaxis_title="Total",
    )
    serialized_data = [
        {**point, "period": _serialize_datetime(point.get("period"))}
        for point in data_points
    ]
    return {
        "organizacao_id": str(organizacao_id),
        "months": months,
        "data": serialized_data,
        "chart": chart,
    }


def get_nucleo_metrics(organizacao_id: str, nucleo_id: str) -> dict[str, Any]:
    """Retorna métricas consolidadas de um núcleo específico limitado à organização informada."""

    nucleo = (
        Nucleo.objects.filter(organizacao_id=organizacao_id, id=nucleo_id, deleted=False)
        .values("id", "nome", "organizacao_id")
        .first()
    )
    if not nucleo:
        return {
            "organizacao_id": str(organizacao_id),
            "nucleo_id": nucleo_id,
            "error": "Núcleo não encontrado para a organização.",
        }

    return {
        "organizacao_id": str(organizacao_id),
        "nucleo": {**nucleo, "id": str(nucleo["id"])} if nucleo else None,
        "total_membros": nucleos_metrics.get_total_membros(nucleo_id),
        "total_suplentes": nucleos_metrics.get_total_suplentes(nucleo_id),
        "membros_por_status": nucleos_metrics.get_membros_por_status(nucleo_id),
        "taxa_participacao": nucleos_metrics.get_taxa_participacao(organizacao_id),
    }


def get_organizacao_description(organizacao_id: str) -> dict[str, Any]:
    """Retorna descrição e metadados básicos da organização para uso em contexto de RAG."""

    try:
        uuid.UUID(str(organizacao_id))
    except ValueError:
        return {"organizacao_id": organizacao_id, "error": "Organização não encontrada."}

    organizacao = (
        Organizacao.objects.filter(id=organizacao_id, deleted=False)
        .values("id", "nome", "descricao", "tipo", "cidade", "estado", "site")
        .first()
    )
    return organizacao or {"organizacao_id": organizacao_id, "error": "Organização não encontrada."}


def get_organizacao_nucleos_context(organizacao_id: str) -> dict[str, Any]:
    """Retorna lista de núcleos ativos da organização com dados relevantes para contexto RAG."""

    nucleos = list(
        Nucleo.objects.filter(organizacao_id=organizacao_id, ativo=True, deleted=False)
        .values("id", "nome", "descricao", "classificacao")
        .order_by("nome")
    )
    return {
        "organizacao_id": str(organizacao_id),
        "nucleos": [{**nucleo, "id": str(nucleo["id"])} for nucleo in nucleos],
    }


def get_future_events_context(
    organizacao_id: str,
    *,
    limit: int | None = 10,
    from_date: datetime | None = None,
    nucleo_ids: Iterable[str] | None = None,
) -> dict[str, Any]:
    """Retorna eventos futuros da organização filtrados para composição de contexto RAG."""

    reference = from_date or timezone.now()
    queryset = Evento.objects.filter(
        organizacao_id=organizacao_id,
        data_inicio__gte=reference,
        deleted=False,
    ).values(
        "id",
        "titulo",
        "descricao",
        "data_inicio",
        "data_fim",
        "local",
        "nucleo_id",
    )

    if nucleo_ids:
        queryset = queryset.filter(nucleo_id__in=list(nucleo_ids))

    events = list(queryset.order_by("data_inicio"))
    if limit is not None:
        events = events[:limit]

    return {
        "organizacao_id": str(organizacao_id),
        "from_date": _serialize_datetime(reference),
        "events": [
            {
                **event,
                "id": str(event.get("id")),
                "nucleo_id": str(event.get("nucleo_id")) if event.get("nucleo_id") else None,
                "data_inicio": _serialize_datetime(event.get("data_inicio")),
                "data_fim": _serialize_datetime(event.get("data_fim")),
            }
            for event in events
        ],
    }


User = get_user_model()


def _associado_nome(usuario: Any) -> str:
    nome = (getattr(usuario, "contato", "") or "").strip()
    if nome:
        return nome
    username = (getattr(usuario, "username", "") or "").strip()
    return username or "Usuário"


def get_associados_list(organizacao_id: str) -> dict[str, Any]:
    """Retorna lista de associados ativos da organização com campos não sensíveis."""

    cache_key = f"ai_chat:associados:{organizacao_id}"
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    associados = list(
        User.objects.filter(
            organizacao_id=organizacao_id,
            is_associado=True,
            deleted=False,
            is_active=True,
        )
        .only("id", "contato", "username", "created_at")
        .order_by("contato", "username")
    )
    data = {
        "organizacao_id": str(organizacao_id),
        "associados": [
            {
                "id": str(associado.id),
                "nome": _associado_nome(associado),
                "data_de_ingresso": _serialize_datetime(getattr(associado, "created_at", None)),
                "status": "ativo",
            }
            for associado in associados
        ],
    }
    cache.set(cache_key, data, timeout=300)
    return data


def get_nucleados_list(organizacao_id: str, nucleo_id: str) -> dict[str, Any]:
    """Retorna nucleados ativos de um núcleo específico dentro da organização informada."""

    participacoes = (
        ParticipacaoNucleo.objects.select_related("user", "nucleo")
        .filter(
            nucleo_id=nucleo_id,
            nucleo__organizacao_id=organizacao_id,
            user__organizacao_id=organizacao_id,
            status="ativo",
            status_suspensao=False,
            deleted=False,
        )
        .only(
            "id",
            "status",
            "papel",
            "papel_coordenador",
            "data_solicitacao",
            "nucleo",
            "user__id",
            "user__contato",
            "user__username",
        )
        .order_by("user__contato", "user__username")
    )
    return {
        "organizacao_id": str(organizacao_id),
        "nucleo_id": str(nucleo_id),
        "nucleados": [
            {
                "id": str(participacao.user.id),
                "nome": _associado_nome(participacao.user),
                "status": participacao.status,
                "papel": participacao.papel,
                "data_de_ingresso": _serialize_datetime(participacao.data_solicitacao),
            }
            for participacao in participacoes
        ],
    }


def get_nucleos_list(organizacao_id: str) -> dict[str, Any]:
    """Retorna núcleos ativos da organização com dados essenciais."""

    nucleos = list(
        Nucleo.objects.filter(organizacao_id=organizacao_id, ativo=True, deleted=False)
        .only("id", "nome", "classificacao", "consultor_id")
        .order_by("nome")
    )
    return {
        "organizacao_id": str(organizacao_id),
        "nucleos": [
            {
                "id": str(nucleo.id),
                "nome": nucleo.nome,
                "classificacao": nucleo.classificacao,
                "consultor_id": str(nucleo.consultor_id) if nucleo.consultor_id else None,
            }
            for nucleo in nucleos
        ],
    }


def get_eventos_list(organizacao_id: str, future_only: bool = True) -> dict[str, Any]:
    """Retorna eventos da organização, opcionando limitar a eventos futuros."""

    cache_key = f"ai_chat:eventos:{organizacao_id}:{future_only}"
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    referencia = timezone.now()
    queryset = (
        Evento.objects.select_related("nucleo")
        .filter(organizacao_id=organizacao_id, deleted=False)
        .only("id", "titulo", "data_inicio", "nucleo_id")
    )
    if future_only:
        queryset = queryset.filter(data_inicio__gte=referencia)

    eventos = list(queryset.order_by("data_inicio"))
    data = {
        "organizacao_id": str(organizacao_id),
        "eventos": [
            {
                "id": str(evento.id),
                "titulo": evento.titulo,
                "data_inicio": _serialize_datetime(evento.data_inicio),
                "nucleo_id": str(evento.nucleo_id) if evento.nucleo_id else None,
            }
            for evento in eventos
        ],
    }
    cache.set(cache_key, data, timeout=300)
    return data


def get_inscritos_list(evento_id: str) -> dict[str, Any]:
    """Retorna inscritos de um evento sem expor dados sensíveis."""

    cache_key = f"ai_chat:inscritos:{evento_id}"
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    inscritos = (
        InscricaoEvento.objects.select_related("user", "evento")
        .filter(evento_id=evento_id, deleted=False, evento__deleted=False)
        .only("evento", "user__id", "user__contato", "user__username")
        .order_by("user__contato", "user__username")
    )
    data = {
        "evento_id": evento_id,
        "inscritos": [
            {"id": str(inscricao.user.id), "nome": _associado_nome(inscricao.user)}
            for inscricao in inscritos
        ],
    }
    cache.set(cache_key, data, timeout=300)
    return data
