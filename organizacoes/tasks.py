from __future__ import annotations

from celery import shared_task
from django.dispatch import Signal, receiver
from django.utils.translation import gettext_lazy as _

from notificacoes.services.notificacoes import enviar_para_usuario

from .models import Organizacao

organizacao_alterada = Signal()  # args: organizacao, acao


@shared_task
def enviar_email_membros(organizacao_id: int, acao: str) -> None:
    org = Organizacao.all_objects.get(pk=organizacao_id)
    users = list(org.users.all())
    if not users:
        return
    traducoes = {
        "created": _("criada"),
        "updated": _("atualizada"),
        "deleted": _("excluída"),
        "inactivated": _("inativada"),
        "reactivated": _("reativada"),
    }
    acao_txt = traducoes.get(acao, acao)
    subject = _("Organização %(nome)s %(acao)s") % {"nome": org.nome, "acao": acao_txt}
    message = _("A organização %(nome)s foi %(acao)s.") % {"nome": org.nome, "acao": acao_txt}
    for user in users:
        enviar_para_usuario(
            user,
            "organizacao_alterada",
            {"assunto": subject, "mensagem": message},
        )


@receiver(organizacao_alterada)
def _notify_members(sender, organizacao: Organizacao, acao: str, **kwargs) -> None:
    enviar_email_membros.delay(organizacao.pk, acao)
