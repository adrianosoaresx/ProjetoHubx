from django.urls import include, path
from django.views.i18n import JavaScriptCatalog

urlpatterns = [
    path("jsi18n/", JavaScriptCatalog.as_view(), name="javascript-catalog"),
    path("", include(("dashboard.urls", "dashboard"), namespace="dashboard")),
]
