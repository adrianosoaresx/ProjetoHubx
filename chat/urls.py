from django.urls import path
from . import views

app_name = "chat"

urlpatterns = [
    # Lista de usuários do núcleo para iniciar conversa
    path("", views.chat_index, name="index"),
    # Janela de chat em tempo real com o usuário selecionado
    path("room/<int:user_id>/", views.chat_room, name="room"),
    # Histórico simplificado de mensagens (usado em testes)
    path("conversation/<int:user_id>/", views.conversation, name="conversation"),
]
