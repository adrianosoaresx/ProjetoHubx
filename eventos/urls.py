from agenda.urls import urlpatterns as _agenda_urlpatterns

app_name = "eventos"

# Reaproveita as mesmas views/urls do app antigo
urlpatterns = list(_agenda_urlpatterns)
