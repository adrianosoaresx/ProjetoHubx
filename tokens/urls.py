from django.urls import path

from . import views

app_name = "tokens"

urlpatterns = [
    path("", views.token, name="token"),
    path("novo/", views.criar_token, name="criar_token"),
    path("convites/gerar/", views.GerarTokenConviteView.as_view(), name="gerar_convite"),
    path("convites/validar/", views.ValidarTokenConviteView.as_view(), name="validar_convite"),
    path("codigo/gerar/", views.GerarCodigoAutenticacaoView.as_view(), name="gerar_codigo"),
    path("codigo/validar/", views.ValidarCodigoAutenticacaoView.as_view(), name="validar_codigo"),
    path("2fa/ativar/", views.Ativar2FAView.as_view(), name="ativar_2fa"),
    path("2fa/desativar/", views.Desativar2FAView.as_view(), name="desativar_2fa"),
]
