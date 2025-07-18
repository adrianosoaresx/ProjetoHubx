from django.contrib import admin

from .models import Post


@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ["autor", "tipo_feed"]
    list_filter = ["tipo_feed"]
