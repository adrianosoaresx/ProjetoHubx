from django.urls import path
from . import views

app_name = "chat"

urlpatterns = [
    path("modal/users/", views.modal_user_list, name="modal_users"),
    path("modal/room/<int:user_id>/", views.modal_room, name="modal_room"),
    path("messages/<int:user_id>/", views.messages_history, name="messages_history"),
]
