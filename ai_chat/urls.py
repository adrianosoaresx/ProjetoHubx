from __future__ import annotations

from django.urls import path

from . import views

app_name = "ai_chat"

urlpatterns = [
    path("", views.ChatPageView.as_view(), name="chat"),
    path("sessions/<uuid:session_id>/messages/", views.send_message, name="send_message"),
]
