from django.urls import path

from .views import (
    importar_pagamentos_view,
    inadimplencias_view,
    lancamentos_list_view,
    forecast_view,
    relatorios_view,
    centros_list_view,
    task_log_detail_view,
    task_logs_view,
)

app_name = "financeiro"

urlpatterns = [
    path("importar/", importar_pagamentos_view, name="importar_pagamentos"),
    path("relatorios/", relatorios_view, name="relatorios"),
    path("centros/", centros_list_view, name="centros"),
    path("lancamentos/", lancamentos_list_view, name="lancamentos"),
    path("forecast/", forecast_view, name="forecast"),
    path("inadimplencias/", inadimplencias_view, name="inadimplencias"),
    path("task-logs/", task_logs_view, name="task_logs"),
    path("task-logs/<int:pk>/", task_log_detail_view, name="task_log_detail"),
]
