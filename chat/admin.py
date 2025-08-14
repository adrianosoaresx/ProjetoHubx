from django.contrib import admin

from .models import (
    ChatAttachment,
    ChatChannel,
    ChatMessage,
    ChatNotification,
    RelatorioChatExport,
    ResumoChat,
)


@admin.register(ChatChannel)
class ChatChannelAdmin(admin.ModelAdmin):
    list_display = ["titulo", "retencao_dias", "created_at"]


@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    list_display = ["remetente", "channel", "tipo", "pinned_at", "created_at"]


@admin.register(ChatAttachment)
class ChatAttachmentAdmin(admin.ModelAdmin):
    list_display = ["id", "mime_type", "tamanho", "preview_ready", "created_at"]


@admin.register(ChatNotification)
class ChatNotificationAdmin(admin.ModelAdmin):
    list_display = ["usuario", "mensagem", "lido"]


@admin.register(RelatorioChatExport)
class RelatorioChatExportAdmin(admin.ModelAdmin):
    list_display = ["channel", "formato", "gerado_por", "created_at"]


@admin.register(ResumoChat)
class ResumoChatAdmin(admin.ModelAdmin):
    list_display = ["canal", "periodo", "created_at"]
