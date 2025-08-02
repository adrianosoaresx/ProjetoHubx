from django.contrib import admin

from .models import ChatChannel, ChatMessage, ChatNotification, RelatorioChatExport


@admin.register(ChatChannel)
class ChatChannelAdmin(admin.ModelAdmin):
    list_display = ["titulo", "created_at"]


@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    list_display = ["remetente", "channel", "tipo", "pinned_at", "timestamp"]


@admin.register(ChatNotification)
class ChatNotificationAdmin(admin.ModelAdmin):
    list_display = ["usuario", "mensagem", "lido"]


@admin.register(RelatorioChatExport)
class RelatorioChatExportAdmin(admin.ModelAdmin):
    list_display = ["channel", "formato", "gerado_por", "created_at"]
