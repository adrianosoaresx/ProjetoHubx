from django.urls import path

from .views import (
    aportes_form_view,
    extrato_view,
    forecast_view,
    importar_pagamentos_view,
    inadimplencias_view,
    lancamentos_list_view,
    lancamento_ajuste_modal_view,
    logs_list_view,
    relatorios_view,
    centro_form_view,
    centros_list_view,
    repasses_view,
    integracoes_list_view,
    integracao_form_view,
    task_log_detail_view,
    task_logs_view,
)

app_name = "financeiro"

urlpatterns = [
    path("importar/", importar_pagamentos_view, name="importar_pagamentos"),
    path("aportes/", aportes_form_view, name="aportes_form"),
    path("extrato/", extrato_view, name="extrato"),
    path("relatorios/", relatorios_view, name="relatorios"),
    path("centros/form/", centro_form_view, name="centro_form"),
    path("centros/form/<int:pk>/", centro_form_view, name="centro_form_edit"),
    path("centros/", centros_list_view, name="centros"),
    path("integracoes/form/", integracao_form_view, name="integracao_form"),
    path("integracoes/form/<uuid:pk>/", integracao_form_view, name="integracao_form_edit"),
    path("integracoes/", integracoes_list_view, name="integracoes"),
    path("lancamentos/", lancamentos_list_view, name="lancamentos"),
    path("lancamentos/<int:pk>/ajustar/", lancamento_ajuste_modal_view, name="lancamento_ajustar"),
    path("repasses/", repasses_view, name="repasses"),
    path("logs/", logs_list_view, name="logs"),
    path("forecast/", forecast_view, name="forecast"),
    path("inadimplencias/", inadimplencias_view, name="inadimplencias"),
    path("task-logs/", task_logs_view, name="task_logs"),
    path("task-logs/<int:pk>/", task_log_detail_view, name="task_log_detail"),
]
