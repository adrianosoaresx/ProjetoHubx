from django.urls import path

from .views.pages import (
    aportes_form_view,
    extrato_view,
    importacoes_list_view,
    importar_pagamentos_view,
    lancamento_ajuste_modal_view,
    lancamentos_list_view,
    logs_list_view,
    relatorios_view,
    repasses_view,
    task_log_detail_view,
    task_logs_view,
)

app_name = "financeiro"

urlpatterns = [
    path("importar/", importar_pagamentos_view, name="importar_pagamentos"),
    path("aportes/", aportes_form_view, name="aportes_form"),
    path("extrato/", extrato_view, name="extrato"),
    path("relatorios/", relatorios_view, name="relatorios"),
    path("importacoes/", importacoes_list_view, name="importacoes"),
    path("lancamentos/", lancamentos_list_view, name="lancamentos"),
    path("lancamentos/<uuid:pk>/ajustar/", lancamento_ajuste_modal_view, name="lancamento_ajustar"),
    path("repasses/", repasses_view, name="repasses"),
    path("logs/", logs_list_view, name="logs"),
    path("task-logs/", task_logs_view, name="task_logs"),
    path("task-logs/<int:pk>/", task_log_detail_view, name="task_log_detail"),
]
