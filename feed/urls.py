from django.urls import path

from . import views

app_name = "feed"

urlpatterns = [
    path("", views.FeedListView.as_view(), name="listar"),
    path("mural/", views.meu_mural, name="meu_mural"),
    path("usuario/<str:username>/", views.user_feed, name="usuario"),
    path("favoritos/", views.bookmark_list, name="bookmarks"),
    path("novo/", views.NovaPostagemView.as_view(), name="nova_postagem"),
    path("<uuid:pk>/", views.PostDetailView.as_view(), name="post_detail"),
    path("<uuid:pk>/curtir/", views.toggle_like, name="toggle_like"),
    path("<uuid:pk>/editar/", views.post_update, name="post_update"),
    path("<uuid:pk>/remover/", views.post_delete, name="post_delete"),
]
