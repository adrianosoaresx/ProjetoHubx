from __future__ import annotations

from datetime import datetime
from typing import Iterable, Optional

from django.contrib.auth import get_user_model
from django.db import IntegrityError
from django.utils import timezone

from agenda.models import Evento, EventoLog, InscricaoEvento, Tarefa, TarefaLog
from services.nucleos import user_belongs_to_nucleo

from .metrics import (
    chat_eventos_criados_total,
    chat_mensagens_ocultadas_total,
    chat_mensagens_sinalizadas_total,
    chat_tarefas_criadas_total,
)
from .models import (
    ChatChannel,
    ChatMessage,
    ChatMessageFlag,
    ChatMessageReaction,
    ChatModerationLog,
    ChatParticipant,
)
from .spam import SpamDetector

User = get_user_model()


def criar_canal(
    criador: User,
    contexto_tipo: str,
    contexto_id: Optional[str],
    titulo: Optional[str],
    descricao: Optional[str],
    participantes: Iterable[User],
    imagem=None,
    e2ee_habilitado: bool = False,
) -> ChatChannel:
    """Cria um ``ChatChannel`` e adiciona participantes.

    O ``criador`` sempre será ``is_owner`` e ``is_admin``.
    ``contexto_tipo`` define o escopo da conversa. Validações
    adicionais de permissão serão implementadas futuramente.
    """
    if contexto_tipo != "privado":
        users = [criador] + list(participantes)
        for u in users:
            if not _usuario_no_contexto(u, contexto_tipo, contexto_id):
                raise PermissionError("Usuário não pertence ao contexto informado")
    canal = ChatChannel.objects.create(
        contexto_tipo=contexto_tipo,
        contexto_id=contexto_id,
        titulo=titulo or "",
        descricao=descricao or "",
        imagem=imagem,
        e2ee_habilitado=e2ee_habilitado,
    )
    ChatParticipant.objects.create(channel=canal, user=criador, is_owner=True, is_admin=True)
    for user in participantes:
        if user != criador:
            ChatParticipant.objects.get_or_create(channel=canal, user=user)
    return canal


def _usuario_no_contexto(user: User, contexto_tipo: str, contexto_id: Optional[str]) -> bool:
    """Retorna ``True`` se o ``user`` pertence ao contexto especificado."""
    if contexto_tipo == "organizacao":
        return str(user.organizacao_id) == str(contexto_id)
    if contexto_tipo == "nucleo":
        participa, info, suspenso = user_belongs_to_nucleo(user, contexto_id)
        return participa and info.endswith("ativo") and not suspenso
    if contexto_tipo == "evento":
        return InscricaoEvento.objects.filter(
            user=user, evento_id=contexto_id, status="confirmada"
        ).exists()
    return True


def enviar_mensagem(
    canal: ChatChannel,
    remetente: User,
    tipo: str,
    conteudo: str = "",
    arquivo=None,
    reply_to: ChatMessage | None = None,
    conteudo_cifrado: str = "",
) -> ChatMessage:
    """Salva uma nova mensagem no canal.

    Verifica se ``remetente`` participa do canal e se o ``tipo``
    requer um arquivo ou URL válida.
    """
    if not ChatParticipant.objects.filter(channel=canal, user=remetente).exists():
        raise PermissionError("Usuário não participa do canal.")
    if tipo in {"image", "video", "file"} and not arquivo:
        from django.core.exceptions import ValidationError
        from django.core.validators import URLValidator

        validator = URLValidator()
        try:
            validator(conteudo)
        except ValidationError as exc:  # pragma: no cover - defensive
            raise ValueError("Arquivo obrigatório ou URL de arquivo inválida") from exc
    if reply_to and reply_to.channel_id != canal.id:
        raise ValueError("Mensagem de referência deve ser do mesmo canal")
    detector = SpamDetector()
    is_spam = detector.is_spam(remetente, canal, conteudo)
    msg = ChatMessage.objects.create(
        channel=canal,
        remetente=remetente,
        tipo=tipo,
        conteudo=conteudo,
        conteudo_cifrado=conteudo_cifrado,
        arquivo=arquivo,
        reply_to=reply_to,
        is_spam=is_spam,
    )
    if is_spam:
        ChatModerationLog.objects.create(
            message=msg,
            action="spam",
            moderator=remetente,
            previous_content="",
        )
    return msg


def adicionar_reacao(mensagem: ChatMessage, user: User, emoji: str) -> None:
    """Adiciona uma reação ``emoji`` à ``mensagem`` para ``user``.

    Cada usuário pode reagir apenas uma vez por emoji.
    """
    ChatMessageReaction.objects.get_or_create(
        message=mensagem, user=user, emoji=emoji
    )


def remover_reacao(mensagem: ChatMessage, user: User, emoji: str) -> None:
    """Remove a reação ``emoji`` da ``mensagem`` para ``user`` se existir."""
    ChatMessageReaction.objects.filter(
        message=mensagem, user=user, emoji=emoji
    ).delete()


def sinalizar_mensagem(mensagem: ChatMessage, user: User) -> int:
    """Cria uma flag para ``mensagem`` pelo ``user``.

    Retorna a contagem total de sinalizações após a operação.
    """
    try:
        ChatMessageFlag.objects.create(message=mensagem, user=user)
        chat_mensagens_sinalizadas_total.labels(canal_tipo=mensagem.channel.contexto_tipo).inc()
    except IntegrityError:
        raise ValueError("Mensagem já sinalizada pelo usuário")
    total = mensagem.flags.count()
    if total >= 3 and not mensagem.hidden_at:
        mensagem.hidden_at = timezone.now()
        mensagem.save(update_fields=["hidden_at", "updated_at"])
        chat_mensagens_ocultadas_total.inc()
    return total


def criar_item_de_mensagem(
    mensagem: ChatMessage,
    usuario: User,
    *,
    tipo: str,
    titulo: str,
    descricao: str | None = None,
    inicio: datetime,
    fim: datetime,
):
    """Cria um item de agenda a partir de uma mensagem."""

    if tipo == "evento":
        if not usuario.has_perm("agenda.add_evento"):
            raise PermissionError("Usuário sem permissão")
        if not titulo or not inicio or not fim:
            raise ValueError("Dados obrigatórios ausentes")
        evento = Evento.objects.create(
            titulo=titulo,
            descricao=descricao or "",
            data_inicio=inicio,
            data_fim=fim,
            local="A definir",
            cidade="Cidade",
            estado="SC",
            cep="00000-000",
            coordenador=usuario,
            organizacao=usuario.organizacao,
            nucleo_id=mensagem.channel.contexto_id
            if mensagem.channel.contexto_tipo == "nucleo"
            else None,
            status=0,
            publico_alvo=0,
            numero_convidados=0,
            numero_presentes=0,
            contato_nome=usuario.get_full_name() or usuario.username,
            mensagem_origem=mensagem,
        )
        EventoLog.objects.create(evento=evento, usuario=usuario, acao="criado_via_chat")
        ChatModerationLog.objects.create(
            message=mensagem, action="create_item", moderator=usuario
        )
        chat_eventos_criados_total.inc()
        return evento
    if tipo == "tarefa":
        if not usuario.has_perm("agenda.add_tarefa"):
            raise PermissionError("Usuário sem permissão")
        if not titulo or not inicio or not fim:
            raise ValueError("Dados obrigatórios ausentes")
        tarefa = Tarefa.objects.create(
            titulo=titulo,
            descricao=descricao or "",
            data_inicio=inicio,
            data_fim=fim,
            responsavel=usuario,
            organizacao=usuario.organizacao,
            nucleo_id=mensagem.channel.contexto_id
            if mensagem.channel.contexto_tipo == "nucleo"
            else None,
            mensagem_origem=mensagem,
        )
        TarefaLog.objects.create(tarefa=tarefa, usuario=usuario, acao="criado_via_chat")
        ChatModerationLog.objects.create(
            message=mensagem, action="create_item", moderator=usuario
        )
        chat_tarefas_criadas_total.inc()
        return tarefa
    raise NotImplementedError("Tipo de item desconhecido")
