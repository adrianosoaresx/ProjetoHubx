import base64
import logging

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags

logger = logging.getLogger(__name__)


def _build_qrcode_data_url(qrcode_bytes: bytes) -> str:
    encoded = base64.b64encode(qrcode_bytes).decode()
    return f"data:image/png;base64,{encoded}"


def enviar_email_confirmacao_inscricao(inscricao, qrcode_bytes: bytes) -> None:
    if not getattr(settings, "EMAIL_DELIVERY_ENABLED", True):
        logger.info(
            "email_inscricao_desativado", extra={"inscricao": getattr(inscricao, "pk", None)}
        )
        return

    subject = f"Inscrição confirmada: {inscricao.evento.titulo}"
    html_body = render_to_string(
        "eventos/emails/inscricao_confirmada.html",
        {
            "inscricao": inscricao,
            "evento": inscricao.evento,
            "usuario": inscricao.user,
            "qrcode_data_url": _build_qrcode_data_url(qrcode_bytes),
        },
    )
    text_body = strip_tags(html_body)

    message = EmailMultiAlternatives(
        subject,
        text_body,
        settings.DEFAULT_FROM_EMAIL,
        [inscricao.user.email],
    )
    message.attach_alternative(html_body, "text/html")
    message.attach(
        f"inscricao-{inscricao.pk}.png",
        qrcode_bytes,
        "image/png",
    )

    try:
        message.send()
    except Exception:  # pragma: no cover - falha de integração
        logger.exception(
            "erro_email_confirmacao_inscricao",
            extra={"inscricao": getattr(inscricao, "pk", None)},
        )
        raise
    else:
        logger.info(
            "email_confirmacao_inscricao_enviado",
            extra={"inscricao": getattr(inscricao, "pk", None)},
        )
