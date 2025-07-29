"""Interface para o módulo de notificações do financeiro."""

from __future__ import annotations

import logging
from typing import Any

from django.utils.translation import gettext_lazy as _

from notificacoes.services.notificacoes import enviar_para_usuario

logger = logging.getLogger(__name__)


def enviar_cobranca(user: Any, lancamento: Any) -> None:
    """Envia notificação de cobrança a um usuário."""

    assunto = _("Cobrança pendente")
    corpo = _("Existe um lançamento pendente de pagamento.")
    try:
        enviar_para_usuario(
            user,
            "cobranca_pendente",
            {"assunto": str(assunto), "corpo": str(corpo)},
        )
    except Exception as exc:  # pragma: no cover - integração externa
        logger.error("Falha ao enviar cobrança: %s", exc)


def enviar_inadimplencia(user: Any, lancamento: Any) -> None:
    """Envia notificação de inadimplência a um usuário."""

    assunto = _("Inadimplência")
    corpo = _("Você possui lançamentos vencidos.")
    try:
        enviar_para_usuario(
            user,
            "inadimplencia",
            {"assunto": str(assunto), "corpo": str(corpo)},
        )
    except Exception as exc:  # pragma: no cover - integração externa
        logger.error("Falha ao enviar inadimplência: %s", exc)
