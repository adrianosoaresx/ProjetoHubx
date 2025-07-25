from __future__ import annotations

from datetime import timedelta

from celery import shared_task
from django.conf import settings
from django.core.mail import send_mail
from django.utils import timezone

from .models import Nucleo, ParticipacaoNucleo


@shared_task
def notify_participacao_aprovada(participacao_id: int) -> None:
    part = ParticipacaoNucleo.objects.select_related("user").get(pk=participacao_id)
    send_mail(
        "Participação aprovada",
        "Sua solicitação foi aprovada.",
        settings.DEFAULT_FROM_EMAIL,
        [part.user.email],
    )


@shared_task
def notify_participacao_recusada(participacao_id: int) -> None:
    part = ParticipacaoNucleo.objects.select_related("user").get(pk=participacao_id)
    send_mail(
        "Participação recusada",
        "Sua solicitação foi recusada.",
        settings.DEFAULT_FROM_EMAIL,
        [part.user.email],
    )


@shared_task
def notify_suplente_designado(nucleo_id: int, email: str) -> None:
    nucleo = Nucleo.objects.get(pk=nucleo_id)
    membros = list(nucleo.participacoes.select_related("user").values_list("user__email", flat=True))
    send_mail(
        "Novo coordenador suplente",
        f"Um suplente foi designado no núcleo {nucleo.nome}.",
        settings.DEFAULT_FROM_EMAIL,
        membros,
    )


@shared_task
def notify_exportacao_membros(nucleo_id: int) -> None:
    nucleo = Nucleo.objects.get(pk=nucleo_id)
    emails = list(nucleo.participacoes.select_related("user").values_list("user__email", flat=True))
    if emails:
        send_mail(
            "Exportação de membros",
            f"A lista de membros do núcleo {nucleo.nome} foi exportada.",
            settings.DEFAULT_FROM_EMAIL,
            emails,
        )


@shared_task
def expirar_solicitacoes_pendentes() -> None:
    limite = timezone.now() - timedelta(days=30)
    pendentes = ParticipacaoNucleo.objects.filter(status="pendente", data_solicitacao__lt=limite)
    for p in pendentes:
        p.status = "recusado"
        p.data_decisao = timezone.now()
        p.save(update_fields=["status", "data_decisao"])
        notify_participacao_recusada.delay(p.id)
