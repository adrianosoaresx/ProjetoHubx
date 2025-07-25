from django.contrib import admin

from .models import (
    ChatConversation,
    ChatMessage,
    ChatNotification,
    RelatorioChatExport,
)


@admin.register(ChatConversation)
class ChatConversationAdmin(admin.ModelAdmin):
    list_display = ["titulo", "created_at"]


@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    list_display = ["sender", "conversation", "tipo", "pinned_at", "created_at"]


@admin.register(ChatNotification)
class ChatNotificationAdmin(admin.ModelAdmin):
    list_display = ["user", "mensagem", "lido"]


@admin.register(RelatorioChatExport)
class RelatorioChatExportAdmin(admin.ModelAdmin):
    list_display = ["channel", "formato", "gerado_por", "created_at"]
