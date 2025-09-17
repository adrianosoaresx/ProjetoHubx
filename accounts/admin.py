from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .forms import CustomUserChangeForm, CustomUserCreationForm
from .models import MediaTag, User, UserMedia


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    add_form = CustomUserCreationForm
    form = CustomUserChangeForm
    list_display = ("email", "username", "is_staff")
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        (
            "Personal info",
            {"fields": ("username", "contato", "user_type")},
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
                    "user_type",
                ),
            },
        ),
    )
    list_filter = ("is_staff", "is_superuser")

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs


@admin.register(UserMedia)
class UserMediaAdmin(admin.ModelAdmin):
    list_display = ["user", "file", "publico"]
    list_filter = ["publico"]


@admin.register(MediaTag)
class MediaTagAdmin(admin.ModelAdmin):
    list_display = ["nome"]
