from __future__ import annotations

from datetime import timedelta

from celery import shared_task
from django.utils import timezone

from chat.models import ChatNotification
from notificacoes.services.notificacoes import enviar_para_usuario

from .models import ConfiguracaoConta


def _send_for_frequency(frequency: str) -> None:
    delta = timedelta(days=1 if frequency == "diaria" else 7)
    since = timezone.now() - delta
    configs = ConfiguracaoConta.objects.select_related("user").filter(
        frequencia_notificacoes_email=frequency,
        receber_notificacoes_email=True,
    )
    for config in configs:
        qs = ChatNotification.objects.filter(user=config.user, created_at__gte=since, lido=False)
        if qs.exists():
            enviar_para_usuario(
                config.user,
                "resumo_notificacoes",
                {"quantidade": qs.count()},
            )


@shared_task
def enviar_notificacoes_diarias() -> None:
    _send_for_frequency("diaria")


@shared_task
def enviar_notificacoes_semanais() -> None:
    _send_for_frequency("semanal")
