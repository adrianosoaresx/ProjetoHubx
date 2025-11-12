from django.urls import path

from .views import AdminDashboardView, AssociadoDashboardView, DashboardRouterView

app_name = "dashboard"

urlpatterns = [
    path("", DashboardRouterView.as_view(), name="admin_dashboard"),
    path("associado/", AssociadoDashboardView.as_view(), name="associado_dashboard"),
    path("admin/", AdminDashboardView.as_view(), name="admin_dashboard_admin"),
]
