from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model
import json

from .models import Mensagem, Notificacao
from asgiref.sync import sync_to_async

User = get_user_model()


class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        user = self.scope["user"]
        if not user or not user.is_authenticated:
            await self.close()
            return

        dest_id = self.scope["url_route"]["kwargs"].get("dest_id")
        if not dest_id:
            await self.close()
            return

        self.nucleo_id = getattr(user, "nucleo_id", None)

        dest = await self.get_user(dest_id)
        if not dest or dest.nucleo_id != self.nucleo_id:
            await self.close()
            return

        print("WebSocket conectado por:", user.username, "->", dest_id)

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

    async def receive_json(self, data, **kwargs):
        user = self.scope["user"]
        if not user or not user.is_authenticated or not hasattr(self, "dest"):
            await self.send(text_data=json.dumps({"erro": "destinatário inválido"}))
            return

        message_type = data.get("tipo", "text")
        content = data.get("conteudo", "")

        msg = await database_sync_to_async(Mensagem.objects.create)(
            nucleo_id=self.nucleo_id,
            remetente_id=user.id,
            destinatario_id=self.dest.id,
            tipo=message_type,
            conteudo=content,
        )
        recipient_ids = await database_sync_to_async(list)(
            User.objects.filter(nucleo_id=self.nucleo_id)
            .exclude(id=user.id)
            .values_list("id", flat=True)
        )
        for uid in recipient_ids:
            await database_sync_to_async(Notificacao.objects.create)(
                usuario_id=uid,
                remetente_id=user.id,
                mensagem=msg,
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
