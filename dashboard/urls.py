from django.urls import path

from .views import AdminDashboardView

app_name = "dashboard"

urlpatterns = [
    path("", AdminDashboardView.as_view(), name="admin_dashboard"),
]
