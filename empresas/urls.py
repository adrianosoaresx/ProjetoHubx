from django.urls import path

from . import views
from core.permissions import no_superadmin_required

app_name = "empresas"

urlpatterns = [
    path("", no_superadmin_required(views.EmpresaListView.as_view()), name="lista"),
    path("buscar/", no_superadmin_required(views.buscar), name="buscar"),
    path("nova/", no_superadmin_required(views.EmpresaCreateView.as_view()), name="empresa_criar"),
    path("<uuid:pk>/editar/", no_superadmin_required(views.EmpresaUpdateView.as_view()), name="empresa_editar"),
    path("<uuid:pk>/", no_superadmin_required(views.detalhes_empresa), name="detail"),
    path("tags/", no_superadmin_required(views.TagListView.as_view()), name="tags_list"),
    path("tags/novo/", no_superadmin_required(views.TagCreateView.as_view()), name="tags_create"),
    path("tags/<int:pk>/editar/", no_superadmin_required(views.TagUpdateView.as_view()), name="tags_update"),
    path("tags/<int:pk>/remover/", no_superadmin_required(views.TagDeleteView.as_view()), name="tags_delete"),
    path("<uuid:pk>/remover/", no_superadmin_required(views.EmpresaDeleteView.as_view()), name="remover"),
    path("<uuid:empresa_id>/avaliar/", no_superadmin_required(views.AvaliacaoCreateView.as_view()), name="avaliacao_criar"),
    path(
        "<uuid:empresa_id>/avaliar/editar/",
        no_superadmin_required(views.AvaliacaoUpdateView.as_view()),
        name="avaliacao_editar",
    ),
    path("<uuid:empresa_id>/contatos/novo/", no_superadmin_required(views.adicionar_contato), name="contato_novo"),
    path("contatos/<int:pk>/editar/", no_superadmin_required(views.editar_contato), name="contato_editar"),
    path("contatos/<int:pk>/remover/", no_superadmin_required(views.remover_contato), name="contato_remover"),
    path("<uuid:pk>/historico/", no_superadmin_required(views.EmpresaChangeLogListView.as_view()), name="historico"),
    path("favoritas/", no_superadmin_required(views.FavoritoListView.as_view()), name="favoritas"),
]
