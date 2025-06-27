from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model
from django.db.models import Q
import json

from .models import Mensagem

User = get_user_model()


class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        user = self.scope["user"]
        dest_id = self.scope["url_route"]["kwargs"].get("dest_id")
        if not user.is_authenticated or not dest_id:
            await self.close()
            return

        dest = await self.get_user(dest_id)
        if not dest or dest.nucleo_id != getattr(user, "nucleo_id", None):
            await self.close()
            return

        self.dest = dest
        sorted_ids = sorted([user.id, dest.id])
        self.group_name = f"chat_{sorted_ids[0]}_{sorted_ids[1]}"
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    @database_sync_to_async
    def get_user(self, pk):
        try:
            return User.objects.get(pk=pk)
        except User.DoesNotExist:
            return None

    async def disconnect(self, close_code):
        if hasattr(self, "group_name"):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive(self, text_data=None, bytes_data=None):
        user = self.scope["user"]
        if not text_data:
            return
        data = json.loads(text_data)
        message_type = data.get("tipo", "text")
        content = data.get("conteudo", "")
        msg = Mensagem.objects.create(
            nucleo=user.nucleo,
            remetente=user,
            destinatario=self.dest,
            tipo=message_type,
            conteudo=content,
        )
        await self.channel_layer.group_send(
            self.group_name,
            {
                "type": "chat.message",
                "remetente": user.username,
                "tipo": message_type,
                "conteudo": content,
                "timestamp": msg.criado_em.isoformat(),
            },
        )

    async def chat_message(self, event):
        await self.send(text_data=json.dumps(event))
