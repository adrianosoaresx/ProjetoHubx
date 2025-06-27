from django.urls import path
from . import views

app_name = "chat"

urlpatterns = [
    path("", views.chat_room, name="room"),
    path("<int:user_id>/", views.conversation, name="conversation"),
]
