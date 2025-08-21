from django.urls import path

from . import views

app_name = "notificacoes"

urlpatterns = [
    path("templates/", views.list_templates, name="templates_list"),
    path("templates/novo/", views.create_template, name="template_create"),
    path("templates/<slug:codigo>/editar/", views.edit_template, name="template_edit"),
    path("templates/<slug:codigo>/toggle/", views.toggle_template, name="template_toggle"),
    path("templates/<slug:codigo>/excluir/", views.delete_template, name="template_delete"),
    path("logs/", views.list_logs, name="logs_list"),
    path("historico/", views.historico_notificacoes, name="historico"),
    path("metrics/", views.metrics_dashboard, name="metrics_dashboard"),
]
