from __future__ import annotations

import logging
from typing import Any

from asgiref.sync import async_to_sync
from channels.layers import BaseChannelLayer, get_channel_layer
from django.utils import timezone

from ..models import NotificationLog, NotificationStatus

logger = logging.getLogger(__name__)


def broadcast_notification(log: NotificationLog, titulo: str, mensagem: str) -> None:
    """Publica notificações em tempo real via WebSocket.

    Args:
        log: Registro da notificação enviada.
        titulo: Título exibido no front-end.
        mensagem: Corpo da notificação.
    """

    channel_layer: BaseChannelLayer | None = get_channel_layer()
    if channel_layer is None:  # pragma: no cover - dependente da infra
        logger.warning("channel_layer_unavailable", user_id=log.user_id)
        return

    total_pendentes: int = NotificationLog.objects.filter(
        user_id=log.user_id, status=NotificationStatus.PENDENTE
    ).count()
    payload: dict[str, Any] = {
        "type": "notification.message",
        "event": "notification_message",
        "titulo": titulo,
        "mensagem": mensagem,
        "total": total_pendentes,
        "canal": log.canal,
        "timestamp": timezone.now().isoformat(),
    }

    try:
        async_to_sync(channel_layer.group_send)(f"notificacoes_{log.user_id}", payload)
    except Exception as exc:  # pragma: no cover - camada WS é best-effort
        logger.warning(
            "ws_notify_failed",
            user_id=log.user_id,
            canal=log.canal,
            error=str(exc),
        )

