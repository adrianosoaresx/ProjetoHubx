from django.contrib import admin

from .models import User, NotificationSettings, UserType


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ["username", "email", "tipo", "organizacao", "is_staff"]
    list_filter = ["tipo", "organizacao"]


@admin.register(NotificationSettings)
class NotificationSettingsAdmin(admin.ModelAdmin):
    list_display = ["user", "email_conexoes", "sistema_conexoes"]


@admin.register(UserType)
class UserTypeAdmin(admin.ModelAdmin):
    list_display = ["id", "descricao"]
