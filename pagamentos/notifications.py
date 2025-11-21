from __future__ import annotations

import logging
from typing import Any

from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.translation import gettext as _

from pagamentos.models import Transacao

logger = logging.getLogger(__name__)


def enviar_email_pagamento_aprovado(transacao: Transacao) -> None:
    pedido = transacao.pedido
    if not pedido.email:
        logger.info(
            "email_pagamento_pendente", extra={"pedido_id": pedido.id, "transacao_id": transacao.id}
        )
        return

    assunto = _("Pagamento confirmado - Pedido %(pedido)s") % {"pedido": pedido.id}
    contexto: dict[str, Any] = {
        "pedido": pedido,
        "transacao": transacao,
    }
    html = render_to_string("pagamentos/emails/confirmacao.html", contexto)
    texto = render_to_string("pagamentos/emails/confirmacao.txt", contexto)
    send_mail(assunto, texto, settings.DEFAULT_FROM_EMAIL, [pedido.email], html_message=html)
    logger.info(
        "email_pagamento_enviado",
        extra={"pedido_id": pedido.id, "transacao_id": transacao.id, "destinatario": pedido.email},
    )
