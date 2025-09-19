from django.urls import path

from . import views

app_name = "tokens"

urlpatterns = [
    path("", views.token, name="token"),
    path("convites/", views.listar_convites, name="listar_convites"),
    path("convites/<int:token_id>/revogar/", views.revogar_convite, name="revogar_convite"),
    path("convites/gerar/", views.GerarTokenConviteView.as_view(), name="gerar_convite"),
    path("validar-token/", views.ValidarTokenConviteView.as_view(), name="validar_token"),
    path("gerar-codigo/", views.GerarCodigoAutenticacaoView.as_view(), name="gerar_codigo"),
    path("validar-codigo/", views.ValidarCodigoAutenticacaoView.as_view(), name="validar_codigo"),
    path("ativar-2fa/", views.Ativar2FAView.as_view(), name="ativar_2fa"),
    path("desativar-2fa/", views.Desativar2FAView.as_view(), name="desativar_2fa"),
]
