from django.urls import path

from . import views

app_name = "accounts"

urlpatterns = [
    # Autenticação
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("associados/", views.AssociadoListView.as_view(), name="associados_lista"),
    path(
        "associados/promover/",
        views.AssociadoPromoverListView.as_view(),
        name="associados_promover",
    ),
    path(
        "associados/<int:pk>/promover/form/",
        views.AssociadoPromoverFormView.as_view(),
        name="associado_promover_form",
    ),
    path("associados/novo/", views.OrganizacaoUserCreateView.as_view(), name="associados_adicionar"),
    # Registro de usuário
    path("resend-confirmation/", views.resend_confirmation, name="resend_confirmation"),
    path("password_reset/", views.password_reset, name="password_reset"),
    path(
        "password_reset/<str:code>/",
        views.password_reset_confirm,
        name="password_reset_confirm",
    ),
    path("onboarding/", views.onboarding, name="onboarding"),
    path("nome/", views.nome, name="nome"),
    path("cpf/", views.cpf, name="cpf"),
    path("email/", views.email, name="email"),
    path("usuario/", views.usuario, name="usuario"),
    path("senha/", views.senha, name="senha"),
    path("foto/", views.foto, name="foto"),
    path("termos/", views.termos, name="termos"),
    path("registro_sucesso/", views.registro_sucesso, name="registro_sucesso"),
    path("conta-inativa/", views.conta_inativa, name="inactive"),
    # Perfil
    path("perfil/", views.perfil, name="perfil"),
    path("perfil/<uuid:public_id>/", views.perfil_publico, name="perfil_publico_uuid"),
    path("perfil/<int:pk>/", views.perfil_publico, name="perfil_publico"),

    path("perfil/notificacoes/", views.perfil_notificacoes, name="notificacoes"),
    path("perfil/sections/info/", views.perfil_info, name="perfil_sections_info"),
    path("perfil/sections/conexoes/", views.perfil_conexoes, name="perfil_sections_conexoes"),
    path("perfil/sections/portfolio/", views.perfil_portfolio, name="perfil_sections_portfolio"),
    path(
        "perfil/sections/portfolio/<int:pk>/",
        views.perfil_portfolio_detail,
        name="perfil_sections_portfolio_detail",
    ),
    path(
        "perfil/sections/portfolio/<int:pk>/editar/",
        views.perfil_portfolio_edit,
        name="perfil_sections_portfolio_edit",
    ),
    path(
        "perfil/sections/portfolio/<int:pk>/excluir/",
        views.perfil_portfolio_delete,
        name="perfil_sections_portfolio_delete",
    ),
    path(
        "perfil/conexoes/<int:id>/remover/",
        views.remover_conexao,
        name="remover_conexao",
    ),
    path(
        "perfil/conexoes/<int:id>/solicitar/",
        views.solicitar_conexao,
        name="solicitar_conexao",
    ),
    path(
        "perfil/conexoes/<int:id>/aceitar/",
        views.aceitar_conexao,
        name="aceitar_conexao",
    ),
    path(
        "perfil/conexoes/<int:id>/recusar/",
        views.recusar_conexao,
        name="recusar_conexao",
    ),
    path(
        "perfil/conexoes/buscar/",
        views.perfil_conexoes_buscar,
        name="perfil_conexoes_buscar",
    ),

    path(
        "perfil/partials/portfolio/",
        views.perfil_section,
        {"section": "portfolio"},
        name="perfil_portfolio",
    ),
    path(
        "perfil/partials/info/",
        views.perfil_section,
        {"section": "info"},
        name="perfil_info_partial",
    ),
    path(
        "perfil/partials/conexoes/",
        views.perfil_section,
        {"section": "conexoes"},
        name="perfil_conexoes_partial",
    ),
    # Portfólio
    path("perfil/portfolio/", views.perfil_portfolio, name="portfolio"),
    path("perfil/portfolio/<int:pk>/", views.perfil_portfolio_detail, name="portfolio_detail"),
    path("perfil/portfolio/<int:pk>/editar/", views.perfil_portfolio_edit, name="portfolio_edit"),
    path(
        "perfil/portfolio/<int:pk>/excluir/",
        views.perfil_portfolio_delete,
        name="portfolio_delete",
    ),

    path("perfil/<str:username>/", views.perfil_publico, name="perfil_publico_username"),
    path("excluir/", views.excluir_conta, name="excluir_conta"),
    path(
        "confirmar-email/<str:token>/",
        views.confirmar_email,
        name="confirmar_email",
    ),
    path(
        "cancelar-exclusao/<str:token>/",
        views.cancel_delete,
        name="cancel_delete",
    ),
    path("check-2fa/", views.check_2fa, name="check_2fa"),
]
