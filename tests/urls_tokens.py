from django.urls import include, path

from rest_framework.routers import DefaultRouter

from tokens.api import TokenViewSet

router = DefaultRouter()
router.register(r"tokens", TokenViewSet, basename="token")

urlpatterns = [
    path("api/tokens/", include((router.urls, "tokens_api"), namespace="tokens_api")),
]
