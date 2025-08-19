from django.urls import include, path

urlpatterns = [
    path("", include(("dashboard.urls", "dashboard"), namespace="dashboard")),
]
