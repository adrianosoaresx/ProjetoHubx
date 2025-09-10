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
    try:
        part = ParticipacaoNucleo.all_objects.select_related("user").get(pk=participacao_id)
    except ParticipacaoNucleo.DoesNotExist:
        logger.warning(
            "participacao_nucleo_not_found",
            extra={"participacao_id": str(participacao_id)},
        )
        return
    enviar_para_usuario(
        part.user,
        "participacao_aprovada",
        {"nucleo": part.nucleo.nome if part.nucleo else ""},
    )


@shared_task
def notify_participacao_recusada(participacao_id: int) -> None:
    try:
        part = ParticipacaoNucleo.all_objects.select_related("user").get(pk=participacao_id)
    except ParticipacaoNucleo.DoesNotExist:
        logger.warning(
            "participacao_nucleo_not_found",
            extra={"participacao_id": str(participacao_id)},
        )
        return
    enviar_para_usuario(
        part.user,
        "participacao_recusada",
        {"nucleo": part.nucleo.nome if part.nucleo else ""},
    )


@shared_task
def notify_suplente_designado(nucleo_id: int, email: str) -> None:
    """Notifica apenas o suplente designado identificado pelo e-mail."""
    nucleo = Nucleo.objects.get(pk=nucleo_id)
    participacao = nucleo.participacoes.select_related("user").filter(user__email=email).first()
    if participacao:
        enviar_para_usuario(
            participacao.user,
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
    """Limpa contadores de convites de núcleo do cache.

    Tenta usar ``delete_pattern`` quando disponível. Para backends que não
    oferecem esse método (como ``LocMemCache``), itera manualmente pelas chaves
    armazenadas e remove aquelas que iniciam com o prefixo esperado.
    """

    prefix = "convites_nucleo:"
    pattern = f"{prefix}*"
    if hasattr(cache, "delete_pattern"):
        cache.delete_pattern(pattern)  # type: ignore[attr-defined]
        return

    version = getattr(cache, "version", 1)
    internal_prefix = f":{version}:{prefix}"
    try:
        keys = [
            k.split(f":{version}:", 1)[1]
            for k in getattr(cache, "_cache").keys()
            if isinstance(k, str) and k.startswith(internal_prefix)
        ]
    except AttributeError:
        keys = []

    if keys:
        cache.delete_many(keys)


@shared_task
def expirar_convites_nucleo() -> None:
    agora = timezone.now()
    expirados = ConviteNucleo.objects.filter(usado_em__isnull=True, data_expiracao__lt=agora)
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
