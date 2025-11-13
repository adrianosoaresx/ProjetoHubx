from django.urls import path

from .views import (
    AdminDashboardView,
    AssociadoDashboardView,
    ConsultorDashboardView,
    CoordenadorDashboardView,
    DashboardRouterView,
)

app_name = "dashboard"

urlpatterns = [
    path("", DashboardRouterView.as_view(), name="admin_dashboard"),
    path("associado/", AssociadoDashboardView.as_view(), name="associado_dashboard"),
    path("admin/", AdminDashboardView.as_view(), name="admin_dashboard_admin"),
    path("coordenador/", CoordenadorDashboardView.as_view(), name="coordenador_dashboard"),
    path("consultor/", ConsultorDashboardView.as_view(), name="consultor_dashboard"),
]
