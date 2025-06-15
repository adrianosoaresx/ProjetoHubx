from django.urls import path

from . import views

app_name = "empresas"

urlpatterns = [
    path("", views.lista_empresas, name="lista"),
    path("nova/", views.nova_empresa, name="nova"),
    path("<int:pk>/editar/", views.editar_empresa, name="editar"),
    path("busca/", views.buscar_empresas, name="buscar"),
]
