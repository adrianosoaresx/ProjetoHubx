from django.contrib import admin

from .models import (
    User,
    NotificationSettings,
    UserType,
    UserMedia,
    MediaTag,
)


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ["username", "email", "tipo", "organization", "is_staff"]
    list_filter = ["tipo", "organization"]

    def get_queryset(self, request):
        qs = super().get_queryset(request).select_related("organization")
        if request.user.is_superuser:
            return qs
        return qs.filter(organization=request.user.organization)


@admin.register(NotificationSettings)
class NotificationSettingsAdmin(admin.ModelAdmin):
    list_display = ["user", "email_conexoes", "sistema_conexoes"]


@admin.register(UserType)
class UserTypeAdmin(admin.ModelAdmin):
    list_display = ["id", "descricao"]


@admin.register(UserMedia)
class UserMediaAdmin(admin.ModelAdmin):
    list_display = ["user", "file", "uploaded_at"]


@admin.register(MediaTag)
class MediaTagAdmin(admin.ModelAdmin):
    list_display = ["nome"]
