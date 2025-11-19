from django.contrib import admin

from .models import Post


@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ["autor", "tipo_feed", "organizacao", "has_link_preview"]
    list_filter = ["tipo_feed", "organizacao"]
    readonly_fields = ["link_preview"]

    def has_link_preview(self, obj: Post) -> bool:  # pragma: no cover - admin helper
        return bool(obj.link_preview)

    has_link_preview.short_description = "Prévia"
    has_link_preview.boolean = True
