from __future__ import annotations

from datetime import timedelta

from celery import shared_task
from django.utils import timezone

from notificacoes.services.notificacoes import enviar_para_usuario

from .models import Nucleo, ParticipacaoNucleo


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
    nucleo = Nucleo.objects.get(pk=nucleo_id)
    participacoes = nucleo.participacoes.select_related("user")
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
