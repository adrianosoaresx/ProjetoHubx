from __future__ import annotations

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.contrib.auth import get_user_model
import time

from .models import ChatChannel, ChatMessage, ChatNotification, ChatParticipant
from .services import adicionar_reacao, enviar_mensagem
from .metrics import chat_websocket_latency_seconds

User = get_user_model()


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
    arquivo = kwargs.get("arquivo")
    return enviar_mensagem(
        canal=channel,
        remetente=remetente,
        tipo=tipo,
        conteudo=conteudo,
        arquivo=arquivo,
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
        if message.tipo != "text":
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
                    "conteudo": message.conteudo,
                    "tipo": message.tipo,
                    "resumo": resumo,
                    "created": notif.created.isoformat(),
                },
            )
        chat_websocket_latency_seconds.observe(time.monotonic() - start)


def add_reaction(message: ChatMessage, emoji: str) -> None:
    adicionar_reacao(message, emoji)
