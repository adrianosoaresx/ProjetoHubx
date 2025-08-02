from __future__ import annotations

import logging
from datetime import timedelta

from celery import shared_task
from django.db import models
from django.utils import timezone

from agenda.models import Evento
from chat.models import ChatNotification
from feed.models import Post
from notificacoes.services.notificacoes import enviar_para_usuario

from .models import ConfiguracaoConta

logger = logging.getLogger(__name__)


def _send_for_frequency(frequency: str) -> None:
    delta = timedelta(days=1 if frequency == "diaria" else 7)
    since = timezone.now() - delta
    configs = ConfiguracaoConta.objects.select_related("user").filter(
        (
            models.Q(frequencia_notificacoes_email=frequency, receber_notificacoes_email=True)
            | models.Q(
                frequencia_notificacoes_whatsapp=frequency,
                receber_notificacoes_whatsapp=True,
            )
        )
    )
    for config in configs:
        counts = {
            "chat": ChatNotification.objects.filter(usuario=config.user, created_at__gte=since, lido=False).count(),
            "feed": Post.objects.filter(created_at__gte=since).exclude(autor=config.user).count(),
            "eventos": Evento.objects.filter(created_at__gte=since).exclude(coordenador=config.user).count(),
        }
        if sum(counts.values()) == 0:
            continue
        if config.receber_notificacoes_email and config.frequencia_notificacoes_email == frequency:
            enviar_para_usuario(config.user, "resumo_notificacoes", counts)
        if config.receber_notificacoes_whatsapp and config.frequencia_notificacoes_whatsapp == frequency:
            enviar_notificacao_whatsapp(config.user, counts)


def enviar_notificacao_whatsapp(user, contexto):
    """Stub para envio via WhatsApp."""
    logger.info("WhatsApp não implementado para %s: %s", user, contexto)


@shared_task
def enviar_notificacoes_diarias() -> None:
    _send_for_frequency("diaria")


@shared_task
def enviar_notificacoes_semanais() -> None:
    _send_for_frequency("semanal")
