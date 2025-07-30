from django.urls import path

from . import views

app_name = "accounts"

urlpatterns = [
    # Autenticação
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("", views.login_view, name="root_login"),
    # Registro de usuário
    path("register/", views.register_view, name="register"),
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
    # Perfil
    path("perfil/", views.perfil_home, name="perfil"),
    path("perfil/informacoes/", views.perfil_informacoes, name="informacoes_pessoais"),
    path("perfil/redes-sociais/", views.perfil_redes_sociais, name="redes_sociais"),
    path("perfil/seguranca/", views.perfil_seguranca, name="seguranca"),
    path("perfil/notificacoes/", views.perfil_notificacoes, name="notificacoes"),
    path("perfil/conexoes/", views.perfil_conexoes, name="conexoes"),
    path(
        "perfil/conexoes/<int:id>/remover/",
        views.remover_conexao,
        name="remover_conexao",
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
]
