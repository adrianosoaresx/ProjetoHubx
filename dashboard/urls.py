from django.urls import path

from . import views

app_name = "dashboard"

urlpatterns = [
    path("", views.dashboard_redirect, name="dashboard"),
    path("root/", views.RootDashboardView.as_view(), name="root"),
    path("admin/", views.AdminDashboardView.as_view(), name="admin"),
    path("coordenador/", views.CoordenadorDashboardView.as_view(), name="coordenador"),
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
    path("configs/<uuid:pk>/edit/", views.DashboardConfigUpdateView.as_view(), name="config-edit"),
    path("configs/<uuid:pk>/delete/", views.DashboardConfigDeleteView.as_view(), name="config-delete"),
    path("configs/<uuid:pk>/apply/", views.DashboardConfigApplyView.as_view(), name="config-apply"),
    path("filters/", views.DashboardFilterListView.as_view(), name="filters"),
    path("filters/create/", views.DashboardFilterCreateView.as_view(), name="filter-create"),
    path("filters/<int:pk>/edit/", views.DashboardFilterUpdateView.as_view(), name="filter-edit"),
    path("filters/<int:pk>/apply/", views.DashboardFilterApplyView.as_view(), name="filter-apply"),
    path("filters/<int:pk>/delete/", views.DashboardFilterDeleteView.as_view(), name="filter-delete"),

    path("achievements/", views.AchievementListView.as_view(), name="achievements"),

    path("layouts/", views.DashboardLayoutListView.as_view(), name="layouts"),
    path("layouts/create/", views.DashboardLayoutCreateView.as_view(), name="layout-create"),
    path("layouts/<int:pk>/edit/", views.DashboardLayoutUpdateView.as_view(), name="layout-edit"),
    path("layouts/<int:pk>/delete/", views.DashboardLayoutDeleteView.as_view(), name="layout-delete"),
    path("layouts/<int:pk>/save/", views.DashboardLayoutSaveView.as_view(), name="layout-save"),

    path("custom-metrics/", views.DashboardCustomMetricListView.as_view(), name="custom-metrics"),
    path("custom-metrics/create/", views.DashboardCustomMetricCreateView.as_view(), name="custom-metric-create"),
    path("custom-metrics/<int:pk>/edit/", views.DashboardCustomMetricUpdateView.as_view(), name="custom-metric-edit"),
    path("custom-metrics/<int:pk>/delete/", views.DashboardCustomMetricDeleteView.as_view(), name="custom-metric-delete"),

]
