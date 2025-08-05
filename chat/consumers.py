from __future__ import annotations

import logging
import time
from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer

from .api import notify_users
from .models import ChatChannel, ChatMessage, ChatMessageReaction, ChatParticipant
from .services import (
    adicionar_reacao,
    remover_reacao,
    enviar_mensagem,
    sinalizar_mensagem,
)
from .metrics import chat_message_latency_seconds

logger = logging.getLogger(__name__)


class ChatConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        user = self.scope["user"]
        if not user or not user.is_authenticated:
            await self.close()
            return
        channel_id = self.scope["url_route"].get("kwargs", {}).get("channel_id")
        try:
            channel = await database_sync_to_async(ChatChannel.objects.get)(pk=channel_id)
        except ChatChannel.DoesNotExist:
            await self.close()
            return
        is_participant = await database_sync_to_async(
            ChatParticipant.objects.filter(channel=channel, user=user).exists
        )()
        if not is_participant:
            if channel.contexto_tipo in {"nucleo", "evento", "organizacao"}:
                attr = f"{channel.contexto_tipo}_id"
                if getattr(user, attr, None) != channel.contexto_id:
                    await self.close()
                    return
            else:
                await self.close()
                return
        self.channel = channel
        self.group_name = f"chat_{channel.id}"
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        if hasattr(self, "group_name"):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive_json(self, data, **kwargs):
        message_type = data.get("tipo")
        user = self.scope["user"]
        if message_type in {"text", "image", "video", "file"}:
            conteudo = data.get("conteudo", "")
            arquivo = None
            start = time.monotonic()
            msg = await database_sync_to_async(enviar_mensagem)(self.channel, user, message_type, conteudo, arquivo)
            await database_sync_to_async(notify_users)(self.channel, msg)
            payload = {
                "type": "chat.message",
                "id": str(msg.id),
                "remetente": user.username,
                "tipo": msg.tipo,
                "conteudo": msg.conteudo,
                "arquivo_url": msg.arquivo.url if msg.arquivo else None,
                "created": msg.created.isoformat(),
                "reactions": msg.reaction_counts(),
            }
            await self.channel_layer.group_send(self.group_name, payload)
            duration = time.monotonic() - start
            chat_message_latency_seconds.observe(duration)
            logger.info("chat message %s sent in %.4fs", msg.id, duration)
        elif message_type == "reaction":
            msg_id = data.get("mensagem_id")
            emoji = data.get("emoji")
            if not msg_id or not emoji:
                return
            msg = await database_sync_to_async(ChatMessage.objects.get)(pk=msg_id)
            exists = await database_sync_to_async(
                ChatMessageReaction.objects.filter(message=msg, user=user, emoji=emoji).exists
            )()
            if exists:
                await database_sync_to_async(remover_reacao)(msg, user, emoji)
            else:
                await database_sync_to_async(adicionar_reacao)(msg, user, emoji)
            user_emojis = await database_sync_to_async(
                lambda: list(
                    ChatMessageReaction.objects.filter(message=msg, user=user).values_list(
                        "emoji", flat=True
                    )
                )
            )()
            payload = {
                "type": "chat.message",
                "id": str(msg.id),
                "remetente": msg.remetente.username,
                "tipo": msg.tipo,
                "conteudo": msg.conteudo,
                "arquivo_url": msg.arquivo.url if msg.arquivo else None,
                "created": msg.created.isoformat(),
                "reactions": await database_sync_to_async(msg.reaction_counts)(),
                "actor": user.username,
                "user_reactions": user_emojis,
            }
            await self.channel_layer.group_send(self.group_name, payload)
        elif message_type == "flag":
            msg_id = data.get("mensagem_id")
            if not msg_id:
                return
            msg = await database_sync_to_async(ChatMessage.objects.get)(pk=msg_id)
            try:
                await database_sync_to_async(sinalizar_mensagem)(msg, user)
            except ValueError:
                return
            if msg.hidden_at:
                payload = {
                    "type": "chat.message",
                    "id": str(msg.id),
                    "remetente": msg.remetente.username,
                    "tipo": msg.tipo,
                    "conteudo": msg.conteudo,
                    "arquivo_url": msg.arquivo.url if msg.arquivo else None,
                    "created": msg.created.isoformat(),
                    "reactions": msg.reaction_counts(),
                    "hidden_at": msg.hidden_at.isoformat(),
                }
                await self.channel_layer.group_send(self.group_name, payload)

    async def chat_message(self, event):
        await self.send_json(event)


class NotificationConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        user = self.scope["user"]
        if not user or not user.is_authenticated:
            await self.close()
            return
        self.group_name = f"notifications_{user.id}"
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, code):
        if hasattr(self, "group_name"):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def chat_notification(self, event):
        await self.send_json(event)
