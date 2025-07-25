from __future__ import annotations

from celery import shared_task
from django.conf import settings
from django.core.mail import send_mail
from django.dispatch import Signal, receiver

from .models import AvaliacaoEmpresa

nova_avaliacao = Signal()  # args: avaliacao


@shared_task
def notificar_responsavel(avaliacao_id: str) -> None:
    avaliacao = AvaliacaoEmpresa.objects.select_related("empresa__usuario").get(pk=avaliacao_id)
    email = avaliacao.empresa.usuario.email
    if email:
        send_mail(
            "Nova avaliação",
            f"Sua empresa {avaliacao.empresa.nome} recebeu uma nova avaliação.",
            settings.DEFAULT_FROM_EMAIL,
            [email],
        )


@receiver(nova_avaliacao)
def _on_nova_avaliacao(sender, avaliacao: AvaliacaoEmpresa, **kwargs) -> None:
    notificar_responsavel.delay(str(avaliacao.id))
