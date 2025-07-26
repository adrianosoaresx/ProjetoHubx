from django.urls import path

from . import views

app_name = "feed"

urlpatterns = [
    path("", views.FeedListView.as_view(), name="listar"),
    path("mural/", views.meu_mural, name="meu_mural"),
    path("novo/", views.NovaPostagemView.as_view(), name="nova_postagem"),
    path("<int:pk>/", views.PostDetailView.as_view(), name="post_detail"),
    path("<int:post_id>/comentar/", views.create_comment, name="create_comment"),
    path("<int:post_id>/curtir/", views.toggle_like, name="toggle_like"),
    path("<int:pk>/editar/", views.post_update, name="post_update"),
    path("<int:pk>/remover/", views.post_delete, name="post_delete"),
    path("<int:pk>/moderar/", views.moderar_post, name="post_moderar"),
]
