from django.urls import path

from . import views

app_name = "dashboard"

urlpatterns = [
    path("", views.dashboard_redirect, name="dashboard"),
    path("root/", views.RootDashboardView.as_view(), name="root"),
    path("admin/", views.AdminDashboardView.as_view(), name="admin"),
    path("gerente/", views.GerenteDashboardView.as_view(), name="gerente"),
    path("cliente/", views.ClienteDashboardView.as_view(), name="cliente"),
]
