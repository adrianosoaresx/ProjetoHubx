import logging

from celery import shared_task
from django.contrib.auth import get_user_model

from notificacoes.services.notificacoes import enviar_para_usuario

from .models import BriefingEvento


logger = logging.getLogger(__name__)


@shared_task
def notificar_briefing_status(
    briefing_id: int,
    status: str,
    destinatarios: list[int] | None = None,
    corpo: str | None = None,
) -> None:
    """Notifica mudança de status do briefing."""

    briefing = BriefingEvento.objects.filter(pk=briefing_id).select_related("evento__coordenador").first()
    if not briefing:
        return

    usuarios: list = []
    if briefing.evento.coordenador:
        usuarios.append(briefing.evento.coordenador)

    if destinatarios:
        User = get_user_model()
        extras = User.objects.filter(pk__in=destinatarios)
        usuarios.extend(extras)

    contexto = {"status": status, "mensagem": corpo or ""}
    for user in usuarios:
        enviar_para_usuario(user, "eventos_briefing_status", contexto)

    logger.info("Briefing %s mudou para %s", briefing_id, status)
