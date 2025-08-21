from django.urls import include, path

urlpatterns = [
    path("api/nucleos/", include(("nucleos.api_urls", "nucleos_api"), namespace="nucleos_api")),
]
