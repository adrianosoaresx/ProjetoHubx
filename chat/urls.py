from django.urls import include, path
from rest_framework.routers import DefaultRouter

from . import views
from .api_views import ChatMessageViewSet

app_name = "chat"

router = DefaultRouter()
router.register("api/mensagens", ChatMessageViewSet, basename="mensagem")

urlpatterns = [
    path("", views.conversation_list, name="conversation_list"),
    path("nova/", views.nova_conversa, name="nova_conversa"),
    path("<slug:slug>/", views.conversation_detail, name="conversation_detail"),
    path("", include(router.urls)),
]
