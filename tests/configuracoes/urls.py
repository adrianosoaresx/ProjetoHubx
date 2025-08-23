import asyncio

from django.urls import include, path
from django.http import JsonResponse
from django.db import transaction

from configuracoes.middleware import get_request_info

from configuracoes.views import (
    ConfiguracoesView,
    ConfiguracaoContextualListView,
    ConfiguracaoContextualCreateView,
    ConfiguracaoContextualUpdateView,
    ConfiguracaoContextualDeleteView,
)
@transaction.non_atomic_requests
async def async_middleware_view(request):
    await asyncio.sleep(0)
    ip, agent, fonte = get_request_info()
    return JsonResponse({"ip": ip, "agent": agent, "fonte": fonte})


urlpatterns = [
    path("async-middleware/", async_middleware_view, name="async-middleware"),
    path("configuracoes/", ConfiguracoesView.as_view(), name="configuracoes"),
    path(
        "configuracoes/contextuais/",
        ConfiguracaoContextualListView.as_view(),
        name="configuracoes-contextual-list",
    ),
    path(
        "configuracoes/contextuais/nova/",
        ConfiguracaoContextualCreateView.as_view(),
        name="configuracoes-contextual-create",
    ),
    path(
        "configuracoes/contextuais/<uuid:pk>/editar/",
        ConfiguracaoContextualUpdateView.as_view(),
        name="configuracoes-contextual-update",
    ),
    path(
        "configuracoes/contextuais/<uuid:pk>/remover/",
        ConfiguracaoContextualDeleteView.as_view(),
        name="configuracoes-contextual-delete",
    ),
    path("accounts/", include(("accounts.urls", "accounts"), namespace="accounts")),
    path("", include("Hubx.urls")),
]
