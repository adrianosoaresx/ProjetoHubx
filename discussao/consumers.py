from __future__ import annotations

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from django.contrib.auth.models import AnonymousUser

from services.nucleos import user_belongs_to_nucleo

from .models import TopicoDiscussao


class DiscussionConsumer(AsyncJsonWebsocketConsumer):
    """WebSocket consumer para eventos de tópicos de discussão."""

    async def connect(self):
        self.topico_id = self.scope["url_route"]["kwargs"]["topico_id"]
        user = self.scope.get("user")
        if not user or isinstance(user, AnonymousUser):
            await self.close()
            return
        try:
            topico = await database_sync_to_async(TopicoDiscussao.objects.select_related("nucleo").get)(
                pk=self.topico_id
            )
        except TopicoDiscussao.DoesNotExist:
            await self.close()
            return
        if topico.nucleo_id:
            participa, info, suspenso = await database_sync_to_async(user_belongs_to_nucleo)(
                user, topico.nucleo_id
            )
            if not participa or not info.endswith("ativo") or suspenso:
                await self.close()
                return
        self.group_name = f"discussao_{self.topico_id}"
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):  # pragma: no cover - channels handles
        if hasattr(self, "group_name"):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive_json(self, content, **kwargs):  # pragma: no cover - somente broadcast
        pass

    async def broadcast(self, event):
        await self.send_json(event["data"])
