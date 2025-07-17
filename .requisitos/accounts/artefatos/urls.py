# accounts/urls.py
from django.urls import path
from accounts import views as v

urlpatterns = [
    path("me/", v.PerfilUsuarioView.as_view()),
    path("me/password/", v.TrocarSenhaView.as_view()),
    path("me/preferencias/", v.PreferenciasView.as_view()),
    path("me/nucleos/", v.ParticipacoesView.as_view()),
]
