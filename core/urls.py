from django.urls import path

from . import views

app_name = "core"

urlpatterns = [
    path("", views.home, name="home"),
    path("posts-destaque/", views.posts_highlights, name="posts_highlights"),
    path("sobre/", views.AboutView.as_view(), name="about"),
    path("termos/", views.TermsView.as_view(), name="terms"),
    path("privacidade/", views.PrivacyView.as_view(), name="privacy"),
]
