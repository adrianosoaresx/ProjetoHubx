from __future__ import annotations

import logging
from datetime import timedelta

import sentry_sdk
from celery import shared_task
from django.db import models
from django.utils import timezone

from agenda.models import Evento
from chat.models import ChatNotification
from feed.models import Post
from notificacoes.services.notificacoes import enviar_para_usuario
from notificacoes.services.push_client import send_push
from notificacoes.services.whatsapp_client import send_whatsapp

from .models import ConfiguracaoConta

logger = logging.getLogger(__name__)


def _send_for_frequency(frequency: str) -> None:
    delta = timedelta(days=1 if frequency == "diaria" else 7)
    now = timezone.localtime()
    since = now - delta
    configs = ConfiguracaoConta.objects.select_related("user").filter(
        (
            models.Q(
                frequencia_notificacoes_email=frequency,
                receber_notificacoes_email=True,
            )
            | models.Q(
                frequencia_notificacoes_whatsapp=frequency,
                receber_notificacoes_whatsapp=True,
            )
            | models.Q(
                frequencia_notificacoes_push=frequency,
                receber_notificacoes_push=True,
            )
        )
    )
    if frequency == "diaria":
        configs = configs.filter(
            hora_notificacao_diaria__hour=now.hour,
            hora_notificacao_diaria__minute=now.minute,
        )
    else:
        configs = configs.filter(
            dia_semana_notificacao=now.weekday(),
            hora_notificacao_semanal__hour=now.hour,
            hora_notificacao_semanal__minute=now.minute,
        )
    for config in configs:
        counts = {
            "chat": ChatNotification.objects.filter(usuario=config.user, created_at__gte=since, lido=False).count(),
            "feed": Post.objects.filter(created_at__gte=since).exclude(autor=config.user).count(),
            "eventos": Evento.objects.filter(created_at__gte=since).exclude(coordenador=config.user).count(),
        }
        if sum(counts.values()) == 0:
            continue
        if (
            config.receber_notificacoes_email
            and config.frequencia_notificacoes_email == frequency
        ) or (
            config.receber_notificacoes_push
            and config.frequencia_notificacoes_push == frequency
        ):
            enviar_para_usuario(config.user, "resumo_notificacoes", counts)
        if config.receber_notificacoes_whatsapp and config.frequencia_notificacoes_whatsapp == frequency:
            enviar_notificacao_whatsapp(config.user, counts)
        if config.receber_notificacoes_push and config.frequencia_notificacoes_push == frequency:
            send_push(
                config.user,
                "Resumo: chat={chat}, feed={feed}, eventos={eventos}".format(**counts),
            )


def enviar_notificacao_whatsapp(user, contexto):
    message = "Resumo: chat={chat}, feed={feed}, eventos={eventos}".format(**contexto)
    try:
        send_whatsapp(user, message)
    except Exception as exc:  # pragma: no cover - falha externa
        sentry_sdk.capture_exception(exc)
        logger.exception("Falha ao enviar WhatsApp", extra={"user": getattr(user, "id", None)})


@shared_task
def enviar_notificacoes_diarias() -> None:
    _send_for_frequency("diaria")


@shared_task
def enviar_notificacoes_semanais() -> None:
    _send_for_frequency("semanal")
