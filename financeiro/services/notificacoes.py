"""Interface para o módulo de notificações do financeiro."""

from __future__ import annotations

import logging
from typing import Any

from django.utils.translation import gettext_lazy as _

from .notifications_client import send_email, send_push, send_whatsapp

logger = logging.getLogger(__name__)


def enviar_cobranca(user: Any, lancamento: Any) -> None:
    """Envia notificação de cobrança a um usuário."""

    assunto = _("Cobrança pendente")
    corpo = _("Existe um lançamento pendente de pagamento.")
    try:
        send_email(user, str(assunto), str(corpo))
        send_push(user, str(corpo))
        send_whatsapp(user, str(corpo))
    except Exception as exc:  # pragma: no cover - integração externa
        logger.error("Falha ao enviar cobrança: %s", exc)


def enviar_inadimplencia(user: Any, lancamento: Any) -> None:
    """Envia notificação de inadimplência a um usuário."""

    assunto = _("Inadimplência")
    corpo = _("Você possui lançamentos vencidos.")
    try:
        send_email(user, str(assunto), str(corpo))
        send_push(user, str(corpo))
        send_whatsapp(user, str(corpo))
    except Exception as exc:  # pragma: no cover - integração externa
        logger.error("Falha ao enviar inadimplência: %s", exc)
