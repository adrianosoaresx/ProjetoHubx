from __future__ import annotations

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.contrib.auth import get_user_model
import time
import logging

from .models import ChatChannel, ChatMessage, ChatNotification, ChatParticipant
from .services import adicionar_reacao, remover_reacao, enviar_mensagem
from .metrics import chat_notification_latency_seconds

User = get_user_model()

logger = logging.getLogger(__name__)


def get_user(pk: int):
    try:
        return User.objects.get(pk=pk)
    except User.DoesNotExist:  # pragma: no cover - fallback
        return None


def create_message(**kwargs):
    """Wrapper para enviar_mensagem com resolução de IDs."""
    channel = kwargs.get("channel")
    if not channel and "channel_id" in kwargs:
        channel = ChatChannel.objects.get(pk=kwargs["channel_id"])
    remetente = kwargs.get("remetente")
    if not remetente and "remetente_id" in kwargs:
        remetente = User.objects.get(pk=kwargs["remetente_id"])
    tipo = kwargs.get("tipo", "text")
    conteudo = kwargs.get("conteudo", "")
    conteudo_cifrado = kwargs.get("conteudo_cifrado", "")
    arquivo = kwargs.get("arquivo")
    reply_to = kwargs.get("reply_to")
    if not reply_to and kwargs.get("reply_to_id"):
        reply_to = ChatMessage.objects.get(pk=kwargs["reply_to_id"])
    return enviar_mensagem(
        canal=channel,
        remetente=remetente,
        tipo=tipo,
        conteudo=conteudo,
        arquivo=arquivo,
        reply_to=reply_to,
        conteudo_cifrado=conteudo_cifrado,
    )


def notify_users(channel: ChatChannel, message: ChatMessage) -> None:
    """Cria ``ChatNotification`` e envia via WebSocket."""
    layer = get_channel_layer()
    participants = ChatParticipant.objects.filter(channel=channel).exclude(
        user=message.remetente
    ).select_related("user")
    for participant in participants:
        start = time.monotonic()
        notif = ChatNotification.objects.create(usuario=participant.user, mensagem=message)
        resumo = message.conteudo
        if channel.e2ee_habilitado:
            resumo = ""
        elif message.tipo != "text":
            resumo = message.tipo
        if layer:
            async_to_sync(layer.group_send)(
                f"notifications_{participant.user.id}",
                {
                    "type": "chat.notification",
                    "id": str(notif.id),
                    "mensagem_id": str(message.id),
                    "canal_id": str(channel.id),
                    "canal_titulo": channel.titulo,
                    "canal_url": channel.get_absolute_url(),
                    "conteudo": message.conteudo if not channel.e2ee_habilitado else "",
                    "conteudo_cifrado": message.conteudo_cifrado if channel.e2ee_habilitado else "",
                    "tipo": message.tipo,
                    "resumo": resumo,
                    "reply_to": str(message.reply_to_id) if message.reply_to_id else None,
                    "created": notif.created.isoformat(),
                },
            )
        duration = time.monotonic() - start
        chat_notification_latency_seconds.observe(duration)
        logger.info("chat notification %s sent in %.4fs", notif.id, duration)


def add_reaction(message: ChatMessage, user: User, emoji: str) -> None:
    adicionar_reacao(message, user, emoji)


def remove_reaction(message: ChatMessage, user: User, emoji: str) -> None:
    remover_reacao(message, user, emoji)
