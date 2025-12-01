from django.urls import path

from . import views

app_name = "accounts"

urlpatterns = [
    # Autenticação
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    # Registro de usuário
    path("resend-confirmation/", views.resend_confirmation, name="resend_confirmation"),
    path("password_reset/", views.password_reset, name="password_reset"),
    path(
        "password_reset/<str:code>/",
        views.password_reset_confirm,
        name="password_reset_confirm",
    ),
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
    path("perfil/<uuid:public_id>/avaliar/", views.perfil_avaliar, name="perfil_avaliar"),
    path(
        "perfil/<uuid:public_id>/avaliacoes/carousel/",
        views.perfil_avaliacoes_carousel,
        name="perfil_avaliacoes_carousel",
    ),
    path("perfil/<int:pk>/", views.perfil_publico, name="perfil_publico"),

    path("perfil/notificacoes/", views.perfil_notificacoes, name="notificacoes"),
    path("perfil/sections/info/", views.perfil_info, name="perfil_sections_info"),
    path(
        "perfil/partials/info/",
        views.perfil_section,
        {"section": "info"},
        name="perfil_info_partial",
    ),
    path("perfil/desativar/", views.deactivate_user, name="deactivate_user"),
    path("perfil/ativar/", views.activate_user, name="activate_user"),

    path("perfil/<str:username>/", views.perfil_publico, name="perfil_publico_username"),
    path("excluir/modal/", views.excluir_conta, name="delete_account"),
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
