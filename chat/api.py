from __future__ import annotations

from django.contrib.auth import get_user_model

from .models import ChatChannel, ChatMessage, ChatNotification, ChatParticipant
from .services import adicionar_reacao, enviar_mensagem

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
    """Cria ChatNotification para participantes do canal."""
    for participant in ChatParticipant.objects.filter(channel=channel).exclude(user=message.remetente):
        ChatNotification.objects.create(usuario=participant.user, mensagem=message)


def add_reaction(message: ChatMessage, emoji: str) -> None:
    adicionar_reacao(message, emoji)
