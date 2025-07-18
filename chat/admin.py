from django.contrib import admin

from .models import ChatConversation, ChatMessage, ChatNotification


@admin.register(ChatConversation)
class ChatConversationAdmin(admin.ModelAdmin):
    list_display = ["titulo", "created_at"]


@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    list_display = ["sender", "conversation", "conteudo", "created_at"]


@admin.register(ChatNotification)
class ChatNotificationAdmin(admin.ModelAdmin):
    list_display = ["user", "mensagem", "lido"]
