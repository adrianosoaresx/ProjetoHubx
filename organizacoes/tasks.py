from __future__ import annotations

from celery import shared_task
from django.conf import settings
from django.core.mail import send_mail
from django.dispatch import Signal, receiver

from .models import Organizacao

organizacao_alterada = Signal()  # args: organizacao, acao


@shared_task
def enviar_email_membros(organizacao_id: int, acao: str) -> None:
    org = Organizacao.objects.get(pk=organizacao_id)
    emails = list(org.users.values_list("email", flat=True))
    if not emails:
        return
    subject = f"Organização {org.nome} {acao}"
    message = f"A organização {org.nome} foi {acao}."
    send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, emails)


@receiver(organizacao_alterada)
def _notify_members(sender, organizacao: Organizacao, acao: str, **kwargs) -> None:
    enviar_email_membros.delay(organizacao.pk, acao)
