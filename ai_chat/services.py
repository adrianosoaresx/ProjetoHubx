from __future__ import annotations

from datetime import datetime
import uuid
from typing import Any, Iterable

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.db.models import Q
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
from services.nucleos import user_belongs_to_nucleo


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


def get_organizacao_nucleos_context(
    organizacao_id: str, *, usuario_id: str | None = None, vinculo_id: str | None = None
) -> dict[str, Any]:
    """Retorna lista de núcleos ativos da organização com dados relevantes para contexto RAG."""

    usuario_id = usuario_id or vinculo_id
    base_queryset = Nucleo.objects.filter(organizacao_id=organizacao_id, ativo=True, deleted=False)

    if usuario_id:
        base_queryset = base_queryset.filter(
            Q(consultor_id=usuario_id)
            | Q(
                participacoes__user_id=usuario_id,
                participacoes__status="ativo",
                participacoes__status_suspensao=False,
            )
        )

    nucleos = list(
        base_queryset.values("id", "nome", "descricao", "classificacao").order_by("nome").distinct()
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
    usuario_id: str | None = None,
    vinculo_id: str | None = None,
) -> dict[str, Any]:
    """Retorna eventos futuros da organização filtrados para composição de contexto RAG."""

    usuario_id = usuario_id or vinculo_id
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

    allowed_nucleo_ids: set[str] | None = None
    if usuario_id:
        allowed_nucleo_ids = {
            str(nucleo_id)
            for nucleo_id in Nucleo.objects.filter(
                organizacao_id=organizacao_id,
                ativo=True,
                deleted=False,
            )
            .filter(
                Q(consultor_id=usuario_id)
                | Q(
                    participacoes__user_id=usuario_id,
                    participacoes__status="ativo",
                    participacoes__status_suspensao=False,
                )
            )
            .values_list("id", flat=True)
        }

    if nucleo_ids:
        nucleo_filter_set: set[str] = set()

        numeric_ids: set[int] = set()
        uuid_ids: set[uuid.UUID] = set()
        for raw_id in nucleo_ids:
            try:
                numeric_ids.add(int(str(raw_id)))
                continue
            except (TypeError, ValueError):
                try:
                    uuid_ids.add(uuid.UUID(str(raw_id)))
                except (TypeError, ValueError):
                    continue

        if numeric_ids or uuid_ids:
            nucleo_filter_set = {
                str(pk)
                for pk in Nucleo.objects.filter(
                    organizacao_id=organizacao_id,
                    deleted=False,
                )
                .filter(Q(id__in=numeric_ids) | Q(public_id__in=uuid_ids))
                .values_list("id", flat=True)
            }

        allowed_nucleo_ids = (
            nucleo_filter_set & allowed_nucleo_ids if allowed_nucleo_ids is not None else nucleo_filter_set
        )

    if allowed_nucleo_ids is not None:
        queryset = queryset.filter(nucleo_id__in=list(allowed_nucleo_ids))

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


def _resolve_usuario(usuario_id: str | None = None, vinculo_id: str | None = None):
    resolved_id = usuario_id or vinculo_id
    if not resolved_id:
        return None
    try:
        return User.objects.only("id", "organizacao_id", "user_type", "is_active").get(
            pk=resolved_id, deleted=False
        )
    except User.DoesNotExist:
        return None


def _user_has_organizacao_access(user: Any, organizacao_id: str) -> bool:
    return (
        bool(user)
        and getattr(user, "is_active", False)
        and str(getattr(user, "organizacao_id", "")) == str(organizacao_id)
    )


def _user_has_nucleo_access(
    user: Any, organizacao_id: str, nucleo_id: str, consultor_id: str | None = None
) -> bool:
    if not _user_has_organizacao_access(user, organizacao_id):
        return False

    tipo = getattr(user, "get_tipo_usuario", None)
    if tipo in {"admin", "coordenador", "root"}:
        return True

    if consultor_id and str(consultor_id) == str(getattr(user, "id", None)):
        return True

    participa, _, suspenso = user_belongs_to_nucleo(user, nucleo_id)
    return participa and not suspenso


DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 50


def _normalize_pagination(limit: int | None, offset: int | None) -> tuple[int, int]:
    normalized_limit = DEFAULT_PAGE_SIZE if limit is None else max(1, min(limit, MAX_PAGE_SIZE))
    normalized_offset = max(offset or 0, 0)
    return normalized_limit, normalized_offset


def get_associados_list(
    organizacao_id: str,
    *,
    usuario_id: str | None = None,
    vinculo_id: str | None = None,
    limit: int | None = None,
    offset: int | None = None,
) -> dict[str, Any]:
    """Retorna lista de associados ativos da organização com campos não sensíveis."""

    usuario = _resolve_usuario(usuario_id, vinculo_id)
    if not _user_has_organizacao_access(usuario, organizacao_id):
        return {
            "organizacao_id": str(organizacao_id),
            "associados": [],
            "error": "Você não tem permissão para acessar esta organização.",
        }

    normalized_limit, normalized_offset = _normalize_pagination(limit, offset)
    cache_key = f"ai_chat:associados:{organizacao_id}:{normalized_limit}:{normalized_offset}"
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
        .order_by("contato", "username")[normalized_offset : normalized_offset + normalized_limit]
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


def get_nucleados_list(
    organizacao_id: str,
    nucleo_id: str,
    *,
    usuario_id: str | None = None,
    vinculo_id: str | None = None,
    limit: int | None = None,
    offset: int | None = None,
) -> dict[str, Any]:
    """Retorna nucleados ativos de um núcleo específico dentro da organização informada."""

    nucleo = (
        Nucleo.objects.filter(id=nucleo_id, organizacao_id=organizacao_id, deleted=False)
        .values("id", "consultor_id")
        .first()
    )
    if not nucleo:
        return {
            "organizacao_id": str(organizacao_id),
            "nucleo_id": str(nucleo_id),
            "nucleados": [],
            "error": "Núcleo não encontrado para a organização.",
        }

    usuario = _resolve_usuario(usuario_id, vinculo_id)
    consultor_id = nucleo.get("consultor_id")
    if not _user_has_nucleo_access(
        usuario,
        organizacao_id,
        str(nucleo_id),
        str(consultor_id) if consultor_id else None,
    ):
        return {
            "organizacao_id": str(organizacao_id),
            "nucleo_id": str(nucleo_id),
            "nucleados": [],
            "error": "Você não tem permissão para acessar este núcleo.",
        }

    normalized_limit, normalized_offset = _normalize_pagination(limit, offset)

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
    )[normalized_offset : normalized_offset + normalized_limit]
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


def get_eventos_list(
    organizacao_id: str,
    future_only: bool = True,
    *,
    limit: int | None = None,
    offset: int | None = None,
) -> dict[str, Any]:
    """Retorna eventos da organização, opcionando limitar a eventos futuros."""

    normalized_limit, normalized_offset = _normalize_pagination(limit, offset)

    cache_key = f"ai_chat:eventos:{organizacao_id}:{future_only}:{normalized_limit}:{normalized_offset}"
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

    eventos = list(queryset.order_by("data_inicio")[normalized_offset : normalized_offset + normalized_limit])
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


def get_inscritos_list(
    evento_id: str,
    *,
    usuario_id: str | None = None,
    vinculo_id: str | None = None,
    limit: int | None = None,
    offset: int | None = None,
) -> dict[str, Any]:
    """Retorna inscritos de um evento sem expor dados sensíveis."""

    evento = (
        Evento.objects.filter(id=evento_id, deleted=False)
        .values("id", "organizacao_id", "nucleo_id")
        .first()
    )
    if not evento:
        return {"evento_id": evento_id, "inscritos": [], "error": "Evento não encontrado."}

    usuario = _resolve_usuario(usuario_id, vinculo_id)
    consultor_id: str | None = None
    if evento.get("nucleo_id"):
        consultor_id = (
            Nucleo.objects.filter(
                id=evento["nucleo_id"], organizacao_id=evento["organizacao_id"], deleted=False
            )
            .values_list("consultor_id", flat=True)
            .first()
        )

    if evento.get("nucleo_id") and not _user_has_nucleo_access(
        usuario,
        str(evento["organizacao_id"]),
        str(evento["nucleo_id"]),
        str(consultor_id) if consultor_id else None,
    ):
        return {
            "evento_id": evento_id,
            "inscritos": [],
            "error": "Você não tem permissão para acessar este núcleo.",
        }

    if not _user_has_organizacao_access(usuario, str(evento["organizacao_id"])):
        return {
            "evento_id": evento_id,
            "inscritos": [],
            "error": "Você não tem permissão para acessar esta organização.",
        }

    normalized_limit, normalized_offset = _normalize_pagination(limit, offset)
    cache_key = f"ai_chat:inscritos:{evento_id}:{normalized_limit}:{normalized_offset}"
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    inscritos = (
        InscricaoEvento.objects.select_related("user", "evento")
        .filter(evento_id=evento_id, deleted=False, evento__deleted=False)
        .only("evento", "user__id", "user__contato", "user__username")
        .order_by("user__contato", "user__username")
    )[normalized_offset : normalized_offset + normalized_limit]
    data = {
        "evento_id": evento_id,
        "inscritos": [
            {"id": str(inscricao.user.id), "nome": _associado_nome(inscricao.user)}
            for inscricao in inscritos
        ],
    }
    cache.set(cache_key, data, timeout=300)
    return data
