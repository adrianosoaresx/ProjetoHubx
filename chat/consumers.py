from channels.generic.websocket import AsyncWebsocketConsumer
from django.contrib.auth import get_user_model
from django.db.models import Q
import json

from .models import Mensagem, Notificacao
from asgiref.sync import sync_to_async

User = get_user_model()

class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        user = self.scope["user"]
        if not user.is_authenticated or not getattr(user, "nucleo_id", None):
            await self.close()
            return
        self.nucleo_id = user.nucleo_id
        self.group_name = f"chat_nucleo_{self.nucleo_id}"
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

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
        msg = await sync_to_async(Mensagem.objects.create)(
            nucleo=user.nucleo,
            remetente=user,
            tipo=message_type,
            conteudo=content,
        )
        recipient_ids = await sync_to_async(list)(
            User.objects.filter(nucleo_id=self.nucleo_id)
            .exclude(id=user.id)
            .values_list("id", flat=True)
        )
        for uid in recipient_ids:
            await sync_to_async(Notificacao.objects.create)(
                usuario_id=uid,
                remetente=user,
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
