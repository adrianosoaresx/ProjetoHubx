from __future__ import annotations

from typing import Iterable, Optional

from django.contrib.auth import get_user_model
from django.utils import timezone

from .models import ChatChannel, ChatMessage, ChatParticipant

User = get_user_model()


def criar_canal(
    criador: User,
    contexto_tipo: str,
    contexto_id: Optional[str],
    titulo: Optional[str],
    descricao: Optional[str],
    participantes: Iterable[User],
    imagem=None,
) -> ChatChannel:
    """Cria um ``ChatChannel`` e adiciona participantes.

    O ``criador`` sempre será ``is_owner`` e ``is_admin``.
    ``contexto_tipo`` define o escopo da conversa. Validações
    adicionais de permissão serão implementadas futuramente.
    """
    canal = ChatChannel.objects.create(
        contexto_tipo=contexto_tipo,
        contexto_id=contexto_id,
        titulo=titulo or "",
        descricao=descricao or "",
        imagem=imagem,
    )
    ChatParticipant.objects.create(channel=canal, user=criador, is_owner=True, is_admin=True)
    for user in participantes:
        if user != criador:
            ChatParticipant.objects.get_or_create(channel=canal, user=user)
    return canal


def enviar_mensagem(
    canal: ChatChannel,
    remetente: User,
    tipo: str,
    conteudo: str = "",
    arquivo=None,
) -> ChatMessage:
    """Salva uma nova mensagem no canal.

    Verifica se ``remetente`` participa do canal e se o ``tipo``
    requer um arquivo.
    """
    if not ChatParticipant.objects.filter(channel=canal, user=remetente).exists():
        raise PermissionError("Usuário não participa do canal.")
    if tipo in {"image", "video", "file"} and not arquivo:
        raise ValueError("Arquivo obrigatório para este tipo de mensagem.")
    msg = ChatMessage.objects.create(
        channel=canal,
        remetente=remetente,
        tipo=tipo,
        conteudo=conteudo,
        arquivo=arquivo,
        timestamp=timezone.now(),
    )
    return msg


def adicionar_reacao(mensagem: ChatMessage, emoji: str) -> None:
    """Incrementa a contagem de ``emoji`` na mensagem."""
    reactions = mensagem.reactions or {}
    reactions[emoji] = reactions.get(emoji, 0) + 1
    mensagem.reactions = reactions
    mensagem.save(update_fields=["reactions"])
