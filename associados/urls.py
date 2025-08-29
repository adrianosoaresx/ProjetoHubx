from django.urls import path

from .views import AssociadoListView

app_name = "associados"

urlpatterns = [
    path("", AssociadoListView.as_view(), name="lista"),
]
