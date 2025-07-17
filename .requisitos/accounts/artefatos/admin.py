from django.contrib import admin
from accounts.models import User, ConfiguracaoConta, ParticipacaoNucleo


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ("email", "nome_completo", "is_associado", "is_staff", "is_active")
    search_fields = ("email", "nome_completo", "cpf")
    list_filter = ("is_associado", "is_staff", "is_active", "organizacao")
    readonly_fields = ("last_login", "date_joined")
    ordering = ("email",)


@admin.register(ConfiguracaoConta)
class ConfiguracaoContaAdmin(admin.ModelAdmin):
    list_display = ("user", "tema_escuro", "receber_notificacoes_email", "receber_notificacoes_whatsapp")
    list_filter = ("tema_escuro",)
    search_fields = ("user__email",)


@admin.register(ParticipacaoNucleo)
class ParticipacaoNucleoAdmin(admin.ModelAdmin):
    list_display = ("user", "nucleo", "is_coordenador")
    list_filter = ("is_coordenador", "nucleo__organizacao")
    search_fields = ("user__email", "nucleo__nome")
