from django.urls import path
from . import views

app_name = "chat"

urlpatterns = [
    path("", views.chat_room, name="index"),
    path("room/", views.chat_room, name="room"),

]
