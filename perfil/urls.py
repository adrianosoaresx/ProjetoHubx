from django.urls import path
from . import views

urlpatterns = [
    path('', views.perfil_view, name='perfil'),
    # As rotas de empresas foram movidas para o app ``empresas``. Caso seja
    # necessário reutilizá-las aqui no futuro, descomente as linhas abaixo e
    # implemente as respectivas views em ``perfil/views.py``.
    # path('empresas/', views.empresa_lista, name='empresa_lista'),
    # path('empresas/cadastro/', views.empresa_cadastro, name='empresa_cadastro'),
    # path('empresas/<int:pk>/editar/', views.empresa_editar, name='empresa_editar'),
    # path('empresas/<int:pk>/detalhe/', views.empresa_detalhe, name='empresa_detalhe'),
    # path('empresas/buscar/', views.buscar_empresas, name='buscar_empresas'),
]
