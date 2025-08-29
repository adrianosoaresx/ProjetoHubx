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
    path("perfil/", views.perfil_home, name="perfil"),
    path("perfil/<int:pk>/", views.perfil_publico, name="perfil_publico"),
    path("perfil/informacoes/", views.perfil_informacoes, name="informacoes_pessoais"),
    path("perfil/redes-sociais/", views.perfil_redes_sociais, name="redes_sociais"),
    path("perfil/seguranca/2fa/ativar/", views.enable_2fa, name="enable_2fa"),
    path("perfil/seguranca/2fa/desativar/", views.disable_2fa, name="disable_2fa"),
    path("perfil/notificacoes/", views.perfil_notificacoes, name="notificacoes"),
    path("perfil/conexoes/", views.perfil_conexoes, name="conexoes"),
    path(
        "perfil/conexoes/<int:id>/remover/",
        views.remover_conexao,
        name="remover_conexao",
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
    # Mídias
    path("perfil/midias/", views.perfil_midias, name="midias"),
    path("perfil/midias/<int:pk>/", views.perfil_midia_detail, name="midia_detail"),
    path("perfil/midias/<int:pk>/editar/", views.perfil_midia_edit, name="midia_edit"),
    path(
        "perfil/midias/<int:pk>/excluir/",
        views.perfil_midia_delete,
        name="midia_delete",
    ),
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
