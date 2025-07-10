from django.urls import path
from . import views

app_name = "feed"

urlpatterns = [
    path("", views.feed_global, name="feed"),
    path("mural/", views.meu_mural, name="meu_mural"),
    path("postar/", views.nova_postagem, name="nova_postagem"),
    path("<int:pk>/", views.post_detail, name="post_detail"),
    path("<int:pk>/editar/", views.post_update, name="post_update"),
    path("<int:pk>/remover/", views.post_delete, name="post_delete"),
]
