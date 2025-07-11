from django.urls import path

from . import views

app_name = "agenda"

urlpatterns = [
    path("", views.calendario, name="calendario"),
    path("dia/<slug:dia_iso>/", views.lista_eventos, name="lista_eventos"),
    path("evento/<int:pk>/", views.EventoDetailProxyView.as_view(), name="evento_detail"),
]
