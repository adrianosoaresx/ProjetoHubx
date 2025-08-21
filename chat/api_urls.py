from django.urls import path
from rest_framework.routers import DefaultRouter

from .api_views import (
    AtualizarChavePublicaView,
    ChatAttachmentViewSet,
    ChatChannelCategoryViewSet,
    ChatChannelViewSet,
    ChatFavoriteViewSet,
    ChatMessageViewSet,
    ChatMetricsAPIView,
    ChatNotificationViewSet,
    ChavePublicaView,
    ModeracaoViewSet,
    TrendingTopicsAPIView,
    UploadArquivoAPIView,
    UserChatPreferenceView,
)

router = DefaultRouter()
router.register(r"channels", ChatChannelViewSet, basename="chat-channel")
router.register(r"categorias", ChatChannelCategoryViewSet, basename="chat-categoria")
router.register(r"notificacoes", ChatNotificationViewSet, basename="chat-notificacao")
router.register(r"moderacao/messages", ModeracaoViewSet, basename="chat-moderacao")
router.register(r"favorites", ChatFavoriteViewSet, basename="chat-favorite")
router.register(r"attachments", ChatAttachmentViewSet, basename="chat-attachment")

chat_message_list = ChatMessageViewSet.as_view({"get": "list", "post": "create"})
chat_message_detail = ChatMessageViewSet.as_view(
    {
        "get": "retrieve",
        "patch": "partial_update",
        "delete": "destroy",
    }
)
chat_message_pin = ChatMessageViewSet.as_view({"post": "pin"})
chat_message_unpin = ChatMessageViewSet.as_view({"post": "unpin"})
chat_message_react = ChatMessageViewSet.as_view({"post": "react"})
chat_message_flag = ChatMessageViewSet.as_view({"post": "flag"})
chat_message_restore = ChatMessageViewSet.as_view({"post": "restore"})
chat_message_search = ChatMessageViewSet.as_view({"get": "search"})
chat_message_favorite = ChatMessageViewSet.as_view({"post": "favorite", "delete": "favorite"})
chat_message_create_item = ChatMessageViewSet.as_view({"post": "criar_item"})
chat_message_mark_read = ChatMessageViewSet.as_view({"post": "mark_read"})
chat_channel_config_retention = ChatChannelViewSet.as_view({"patch": "config_retencao"})

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
        "channels/<uuid:channel_pk>/messages/<uuid:pk>/restore/",
        chat_message_restore,
        name="chat-channel-message-restore",
    ),
    path(
        "channels/<uuid:channel_pk>/messages/<uuid:pk>/flag/",
        chat_message_flag,
        name="chat-channel-message-flag",
    ),
    path(
        "channels/<uuid:channel_pk>/messages/<uuid:pk>/favorite/",
        chat_message_favorite,
        name="chat-channel-message-favorite",
    ),
    path(
        "channels/<uuid:channel_pk>/messages/<uuid:pk>/mark-read/",
        chat_message_mark_read,
        name="chat-channel-message-mark-read",
    ),
    path(
        "channels/<uuid:channel_pk>/messages/<uuid:pk>/criar-item/",
        chat_message_create_item,
        name="chat-channel-message-criar-item",
    ),
    path(
        "channels/<uuid:pk>/config-retention/",
        chat_channel_config_retention,
        name="chat-channel-config-retention",
    ),
    path(
        "channels/<uuid:channel_pk>/messages/search/",
        chat_message_search,
        name="chat-channel-message-search",
    ),
    path(
        "moderacao/flags/",
        ModeracaoViewSet.as_view({"get": "list"}),
        name="chat-flags",
    ),
    path("upload/", UploadArquivoAPIView.as_view(), name="chat-upload"),
    path("usuarios/<int:pk>/chave-publica/", ChavePublicaView.as_view(), name="chat-user-public-key"),
    path(
        "usuarios/chave-publica/",
        AtualizarChavePublicaView.as_view(),
        name="chat-user-public-key-update",
    ),
    path("preferencias/", UserChatPreferenceView.as_view(), name="chat-preferences"),
    path("metrics/", ChatMetricsAPIView.as_view(), name="chat-metrics"),
    path("trending/", TrendingTopicsAPIView.as_view(), name="chat-trending"),
]
