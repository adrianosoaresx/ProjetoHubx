from django.contrib import admin
from .models import Post


@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ["autor", "visibilidade", "criado_em"]
    list_filter = ["visibilidade", "criado_em"]
