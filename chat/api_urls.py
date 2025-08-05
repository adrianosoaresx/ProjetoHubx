from django.urls import path
from rest_framework.routers import DefaultRouter

from .api_views import (
    ChatChannelViewSet,
    ChatMessageViewSet,
    ChatNotificationViewSet,
    ModeracaoViewSet,
)

router = DefaultRouter()
router.register(r"channels", ChatChannelViewSet, basename="chat-channel")
router.register(r"notificacoes", ChatNotificationViewSet, basename="chat-notificacao")
router.register(r"moderacao/messages", ModeracaoViewSet, basename="chat-moderacao")

chat_message_list = ChatMessageViewSet.as_view({"get": "list", "post": "create"})
chat_message_detail = ChatMessageViewSet.as_view(
    {
        "get": "retrieve",
        "put": "update",
        "patch": "partial_update",
        "delete": "destroy",
    }
)
chat_message_pin = ChatMessageViewSet.as_view({"post": "pin"})
chat_message_unpin = ChatMessageViewSet.as_view({"post": "unpin"})
chat_message_react = ChatMessageViewSet.as_view({"post": "react"})
chat_message_flag = ChatMessageViewSet.as_view({"post": "flag"})

urlpatterns = router.urls + [
    path(
        "channels/<uuid:channel_pk>/messages/",
        chat_message_list,
        name="chat-channel-messages",
    ),
    path(
        "channels/<uuid:channel_pk>/messages/<uuid:pk>/",
        chat_message_detail,
        name="chat-channel-message-detail",
    ),
    path(
        "channels/<uuid:channel_pk>/messages/<uuid:pk>/pin/",
        chat_message_pin,
        name="chat-channel-message-pin",
    ),
    path(
        "channels/<uuid:channel_pk>/messages/<uuid:pk>/unpin/",
        chat_message_unpin,
        name="chat-channel-message-unpin",
    ),
    path(
        "channels/<uuid:channel_pk>/messages/<uuid:pk>/react/",
        chat_message_react,
        name="chat-channel-message-react",
    ),
    path(
        "channels/<uuid:channel_pk>/messages/<uuid:pk>/flag/",
        chat_message_flag,
        name="chat-channel-message-flag",
    ),
    path(
        "moderacao/flags/",
        ModeracaoViewSet.as_view({"get": "list"}),
        name="chat-flags",
    ),
]

