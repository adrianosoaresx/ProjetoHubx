from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .forms import CustomUserChangeForm, CustomUserCreationForm
from .models import MediaTag, NotificationSettings, User, UserMedia, UserType


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    add_form = CustomUserCreationForm
    form = CustomUserChangeForm
    list_display = ("email", "username", "organization", "is_staff")
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        (
            "Personal info",
            {"fields": ("username", "first_name", "last_name", "organization", "tipo")},
        ),
        (
            "Permissions",
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                )
            },
        ),
        ("Important dates", {"fields": ("last_login", "date_joined")}),
    )
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": (
                    "email",
                    "username",
                    "password1",
                    "password2",
                    "organization",
                    "tipo",
                ),
            },
        ),
    )
    list_filter = ("organization", "is_staff", "is_superuser")

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
