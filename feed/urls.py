from django.urls import path
from . import views

app_name = "feed"

urlpatterns = [
    path("mural/", views.meu_mural, name="meu_mural"),
    path("feed/", views.feed_global, name="feed_global"),
    path("postar/", views.nova_postagem, name="nova_postagem"),
]
