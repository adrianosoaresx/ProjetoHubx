from django.urls import include, path
from django.views.i18n import JavaScriptCatalog

urlpatterns = [
    path('', include(('accounts.urls', 'accounts'), namespace='accounts')),
    path('api/accounts/', include(('accounts.api_urls', 'accounts_api'), namespace='accounts_api')),
    path('empresas/', include(('empresas.urls', 'empresas'), namespace='empresas')),
    path('agenda/', include(('agenda.urls', 'agenda'), namespace='agenda')),
    path('jsi18n/', JavaScriptCatalog.as_view(), name='javascript-catalog'),
]
