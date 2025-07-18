from django.contrib import admin

from .models import Mensagem, Notificacao


@admin.register(Mensagem)
class MensagemAdmin(admin.ModelAdmin):
    list_display = ["remetente", "nucleo", "tipo"]


@admin.register(Notificacao)
class NotificacaoAdmin(admin.ModelAdmin):
    list_display = ["usuario", "remetente", "mensagem", "created_at", "lida"]
