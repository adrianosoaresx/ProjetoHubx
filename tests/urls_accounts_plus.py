from django.urls import include, path
from django.views.generic import RedirectView
from django.views.i18n import JavaScriptCatalog

urlpatterns = [
    path('', include(('accounts.urls', 'accounts'), namespace='accounts')),
    path('api/accounts/', include(('accounts.api_urls', 'accounts_api'), namespace='accounts_api')),
    path('empresas/', include(('empresas.urls', 'empresas'), namespace='empresas')),
    path('eventos/', include(('eventos.urls', 'eventos'), namespace='eventos')),
    path('agenda/<path:rest>/', RedirectView.as_view(url='/eventos/%(rest)s', permanent=True)),
    path('agenda/', RedirectView.as_view(url='/eventos/', permanent=True)),
    path('jsi18n/', JavaScriptCatalog.as_view(), name='javascript-catalog'),
]
