from __future__ import annotations

import logging
import os
from datetime import timedelta

import sentry_sdk
from celery import shared_task
from django.core.cache import cache
from django.db import models
from django.utils import timezone
from twilio.base.exceptions import TwilioRestException  # type: ignore
from twilio.rest import Client  # type: ignore

from agenda.models import Evento
from chat.models import ChatNotification
from feed.models import Post
from notificacoes.services.notificacoes import enviar_para_usuario

from .models import ConfiguracaoConta

logger = logging.getLogger(__name__)


def _send_for_frequency(frequency: str) -> None:
    delta = timedelta(days=1 if frequency == "diaria" else 7)
    now = timezone.localtime()
    since = now - delta
    configs = ConfiguracaoConta.objects.select_related("user").filter(
        (
            models.Q(frequencia_notificacoes_email=frequency, receber_notificacoes_email=True)
            | models.Q(
                frequencia_notificacoes_whatsapp=frequency,
                receber_notificacoes_whatsapp=True,
            )
        )
    )
    minute_window = [
        (now.minute - 1) % 60,
        now.minute,
        (now.minute + 1) % 60,
    ]
    if frequency == "diaria":
        configs = configs.filter(
            hora_notificacao_diaria__hour=now.hour,
            hora_notificacao_diaria__minute__in=minute_window,
        )
    else:
        configs = configs.filter(
            dia_semana_notificacao=now.weekday(),
            hora_notificacao_semanal__hour=now.hour,
            hora_notificacao_semanal__minute__in=minute_window,
        )
    for config in configs:
        window_key = f"resumo:{config.id}:{frequency}:{now.strftime('%Y%m%d%H%M')}"
        if not cache.add(window_key, True, 120):
            continue
        counts = {
            "chat": ChatNotification.objects.filter(usuario=config.user, created_at__gte=since, lido=False).count(),
            "feed": Post.objects.filter(created_at__gte=since).exclude(autor=config.user).count(),
            "eventos": Evento.objects.filter(created__gte=since).exclude(coordenador=config.user).count(),
        }
        if sum(counts.values()) == 0:
            continue
        if config.receber_notificacoes_email and config.frequencia_notificacoes_email == frequency:
            enviar_para_usuario(config.user, "resumo_notificacoes", counts)
        if config.receber_notificacoes_whatsapp and config.frequencia_notificacoes_whatsapp == frequency:
            enviar_notificacao_whatsapp.delay(config.user.id, counts)
@shared_task(bind=True, autoretry_for=(TwilioRestException,), retry_backoff=60, retry_kwargs={"max_retries": 3})
def enviar_notificacao_whatsapp(self, user_id, contexto):
    message = (
        "Resumo: chat={chat}, feed={feed}, eventos={eventos}".format(**contexto)
    )
    try:
        user = ConfiguracaoConta.objects.select_related("user").get(user_id=user_id).user
        client = Client(os.environ.get("TWILIO_ACCOUNT_SID"), os.environ.get("TWILIO_AUTH_TOKEN"))
        client.messages.create(
            body=message,
            from_=os.environ.get("TWILIO_WHATSAPP_FROM"),
            to=f"whatsapp:{user.whatsapp}",
        )
        logger.info("WhatsApp enviado", extra={"user": user_id})
    except TwilioRestException as exc:  # pragma: no cover - falha externa
        sentry_sdk.capture_exception(exc)
        logger.exception("Falha ao enviar WhatsApp", extra={"user": user_id})
        raise


@shared_task
def enviar_notificacoes_diarias() -> None:
    _send_for_frequency("diaria")


@shared_task
def enviar_notificacoes_semanais() -> None:
    _send_for_frequency("semanal")
