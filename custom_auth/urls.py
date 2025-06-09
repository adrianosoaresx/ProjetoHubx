from django.urls import path
from . import views

app_name = 'custom_auth'  # Permite uso de namespace em templates: {% url 'custom_auth:login' %}

urlpatterns = [
    path('', views.login_view, name='root_login'),
    path('login/', views.login_view, name='login'),  # rota base
    path('password_reset/', views.password_reset, name='password_reset'),
    path('onboarding/', views.onboarding, name='onboarding'),
    path('nome/', views.nome, name='nome'),
    path('email/', views.email, name='email'),
    path('token/', views.token, name='token'),
    path('usuario/', views.usuario, name='usuario'),
    path('senha/', views.senha, name='senha'),
    path('foto/', views.foto, name='foto'),
    path('termos/', views.termos, name='termos'),
]
