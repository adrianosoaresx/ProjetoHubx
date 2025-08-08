from django.urls import path
from rest_framework.routers import DefaultRouter

from .api import (
    AceitarConviteAPIView,
    NucleoViewSet,
)

router = DefaultRouter()
router.register(r"nucleos", NucleoViewSet, basename="nucleo")

urlpatterns = router.urls + [
    path(
        "aceitar-convite/",
        AceitarConviteAPIView.as_view(),
        name="nucleo-aceitar-convite",
    ),
]
