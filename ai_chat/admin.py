from django.contrib import admin

from .models import ChatMessage, ChatSession


@admin.register(ChatSession)
class ChatSessionAdmin(admin.ModelAdmin):
    list_display = ("id", "usuario", "organizacao", "status", "created_at")
    list_filter = ("status", "organizacao")
    search_fields = ("id", "usuario__email", "usuario__username")
    autocomplete_fields = ("usuario", "organizacao")


@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    list_display = ("id", "session", "organizacao", "role", "created_at")
    list_filter = ("role", "organizacao")
    search_fields = ("session__id", "content")
    autocomplete_fields = ("session", "organizacao")
    raw_id_fields = ("session",)
