from __future__ import annotations

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer

from .models import TopicoDiscussao


class DiscussionConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self) -> None:  # pragma: no cover - connection handled in tests
        user = self.scope.get("user")
        topico_id = self.scope["url_route"]["kwargs"].get("topico_id")
        if not user or not user.is_authenticated:
            await self.close()
            return
        exists = await database_sync_to_async(
            TopicoDiscussao.objects.filter(pk=topico_id).exists
        )()
        if not exists:
            await self.close()
            return
        self.group_name = f"discussao_{topico_id}"
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, code: int) -> None:  # pragma: no cover - simple
        if hasattr(self, "group_name"):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def discussion_event(self, event: dict) -> None:
        await self.send_json(event)
