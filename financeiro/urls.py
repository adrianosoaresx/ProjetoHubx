from django.urls import path

from .views import (
    importar_pagamentos_view,
    inadimplencias_view,
    lancamentos_list_view,
    relatorios_view,
)

app_name = "financeiro"

urlpatterns = [
    path("importar/", importar_pagamentos_view, name="importar_pagamentos"),
    path("relatorios/", relatorios_view, name="relatorios"),
    path("lancamentos/", lancamentos_list_view, name="lancamentos"),
    path("inadimplencias/", inadimplencias_view, name="inadimplencias"),
]
