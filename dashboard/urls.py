from django.urls import path

from . import views

app_name = "dashboard"

urlpatterns = [
    path("", views.dashboard_redirect, name="dashboard"),
    path("root/", views.RootDashboardView.as_view(), name="root"),
    path("admin/", views.AdminDashboardView.as_view(), name="admin"),
    path("gerente/", views.GerenteDashboardView.as_view(), name="gerente"),
    path("cliente/", views.ClienteDashboardView.as_view(), name="cliente"),
    path("metrics-partial/", views.metrics_partial, name="metrics-partial"),
    path("lancamentos-partial/", views.lancamentos_partial, name="lancamentos-partial"),
    path("notificacoes-partial/", views.notificacoes_partial, name="notificacoes-partial"),
    path("tarefas-partial/", views.tarefas_partial, name="tarefas-partial"),
    path("eventos-partial/", views.eventos_partial, name="eventos-partial"),
    path("export/", views.DashboardExportView.as_view(), name="export"),
    path("export/images/<str:filename>", views.DashboardExportedImageView.as_view(), name="export-image"),
    path("configs/", views.DashboardConfigListView.as_view(), name="configs"),
    path("configs/create/", views.DashboardConfigCreateView.as_view(), name="config-create"),
    path("configs/<uuid:pk>/apply/", views.DashboardConfigApplyView.as_view(), name="config-apply"),
    path("filters/", views.DashboardFilterListView.as_view(), name="filters"),
    path("filters/create/", views.DashboardFilterCreateView.as_view(), name="filter-create"),
    path("filters/<int:pk>/apply/", views.DashboardFilterApplyView.as_view(), name="filter-apply"),
    path("filters/<int:pk>/delete/", views.DashboardFilterDeleteView.as_view(), name="filter-delete"),
    path("achievements/", views.AchievementListView.as_view(), name="achievements"),
]
