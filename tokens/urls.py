from django.urls import path
from . import views

app_name = "tokens"

urlpatterns = [
    path("", views.token, name="token"),
    path("novo/", views.criar_token, name="criar_token"),
]
