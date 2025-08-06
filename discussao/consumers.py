from __future__ import annotations

from channels.generic.websocket import AsyncJsonWebsocketConsumer
from django.contrib.auth.models import AnonymousUser


class DiscussionConsumer(AsyncJsonWebsocketConsumer):
    """WebSocket consumer para eventos de tópicos de discussão."""

    async def connect(self):
        self.topico_id = self.scope["url_route"]["kwargs"]["topico_id"]
        user = self.scope.get("user")
        if not user or isinstance(user, AnonymousUser):
            await self.close()
            return
        self.group_name = f"discussao_{self.topico_id}"
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):  # pragma: no cover - channels handles
        await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive_json(self, content, **kwargs):  # pragma: no cover - somente broadcast
        pass

    async def broadcast(self, event):
        await self.send_json(event["data"])
