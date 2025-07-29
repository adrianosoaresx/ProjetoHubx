from __future__ import annotations

from celery import shared_task
from django.dispatch import Signal, receiver

from notificacoes.services.notificacoes import enviar_para_usuario

from .models import Organizacao

organizacao_alterada = Signal()  # args: organizacao, acao


@shared_task
def enviar_email_membros(organizacao_id: int, acao: str) -> None:
    org = Organizacao.objects.get(pk=organizacao_id)
    users = list(org.users.all())
    if not users:
        return
    subject = f"Organização {org.nome} {acao}"
    message = f"A organização {org.nome} foi {acao}."
    for user in users:
        enviar_para_usuario(
            user,
            "organizacao_alterada",
            {"assunto": subject, "mensagem": message},
        )


@receiver(organizacao_alterada)
def _notify_members(sender, organizacao: Organizacao, acao: str, **kwargs) -> None:
    enviar_email_membros.delay(organizacao.pk, acao)
