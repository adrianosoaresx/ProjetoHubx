"""
URL configuration for Hubx project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from accounts import views as accounts_views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('core.urls')),  # Página inicial
    path('accounts/', include('accounts.urls')),
    # A rota abaixo garante compatibilidade com o valor padrao de
    # ``LOGIN_URL`` caso nao seja definido nas configuracoes.
    path('accounts/login/', accounts_views.login_view, name='accounts_login'),
    path('perfil/', accounts_views.perfil_view, name='perfil'),
    path('empresas/', include('empresas.urls')),
    path('registro/sucesso/', accounts_views.registro_sucesso, name='registro_sucesso'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
