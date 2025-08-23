from __future__ import annotations

import logging
from datetime import timedelta

from celery import shared_task
from django.core.cache import cache
from django.utils import timezone

from notificacoes.services.notificacoes import enviar_para_usuario

from .models import ConviteNucleo, Nucleo, ParticipacaoNucleo

logger = logging.getLogger(__name__)


@shared_task
def notify_participacao_aprovada(participacao_id: int) -> None:
    part = ParticipacaoNucleo.objects.select_related("user").get(pk=participacao_id)
    enviar_para_usuario(
        part.user,
        "participacao_aprovada",
        {"nucleo": part.nucleo.nome if part.nucleo else ""},
    )


@shared_task
def notify_participacao_recusada(participacao_id: int) -> None:
    part = ParticipacaoNucleo.objects.select_related("user").get(pk=participacao_id)
    enviar_para_usuario(
        part.user,
        "participacao_recusada",
        {"nucleo": part.nucleo.nome if part.nucleo else ""},
    )


@shared_task
def notify_suplente_designado(nucleo_id: int, email: str) -> None:
    """Notifica apenas o suplente designado identificado pelo e-mail."""
    nucleo = Nucleo.objects.get(pk=nucleo_id)
    participacoes = nucleo.participacoes.select_related("user").filter(
        user__email=email
    )
    for part in participacoes:
        enviar_para_usuario(
            part.user,
            "suplente_designado",
            {"nucleo": nucleo.nome},
        )


@shared_task
def notify_exportacao_membros(nucleo_id: int) -> None:
    nucleo = Nucleo.objects.get(pk=nucleo_id)
    participacoes = nucleo.participacoes.select_related("user")
    for part in participacoes:
        enviar_para_usuario(
            part.user,
            "exportacao_membros",
            {"nucleo": nucleo.nome},
        )


@shared_task
def expirar_solicitacoes_pendentes() -> None:
    limite = timezone.now() - timedelta(days=30)
    pendentes = ParticipacaoNucleo.objects.filter(status="pendente", data_solicitacao__lt=limite)
    for p in pendentes:
        p.status = "inativo"
        p.data_decisao = timezone.now()
        p.justificativa = "expiração automática"
        p.save(update_fields=["status", "data_decisao", "justificativa"])
        notify_participacao_recusada.delay(p.id)


@shared_task
def limpar_contadores_convites() -> None:
    cache.delete_pattern("convites_nucleo:*")  # type: ignore[attr-defined]


@shared_task
def expirar_convites_nucleo() -> None:
    agora = timezone.now()
    expirados = ConviteNucleo.objects.filter(
        usado_em__isnull=True, data_expiracao__lt=agora
    )
    for convite in expirados:
        convite.usado_em = agora
        convite.save(update_fields=["usado_em"])
        logger.info(
            "convite_expirado",
            extra={
                "convite_id": str(convite.pk),
                "nucleo_id": str(convite.nucleo_id),  # type: ignore[attr-defined]
            },
        )
