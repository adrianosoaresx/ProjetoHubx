from django.urls import path

from . import views

app_name = "chat"

urlpatterns = [
    path("", views.conversation_list, name="conversation_list"),
    path("nova/", views.nova_conversa, name="nova_conversa"),
    path(
        "partials/message/<uuid:message_id>/",
        views.message_partial,
        name="message_partial",
    ),
    path("moderacao/", views.moderacao, name="moderacao"),
    path(
        "<uuid:channel_id>/exportar/",
        views.exportar_modal,
        name="exportar_modal",
    ),
    path(
        "<uuid:channel_id>/historico/",
        views.historico_edicoes,
        name="historico_edicoes",
    ),
    path("<uuid:channel_id>/", views.conversation_detail, name="conversation_detail"),
]
