import asyncio

from django.urls import include, path
from django.http import JsonResponse
from django.db import transaction

from configuracoes.middleware import get_request_info

from configuracoes.views import ConfiguracoesView
@transaction.non_atomic_requests
async def async_middleware_view(request):
    await asyncio.sleep(0)
    ip, agent, fonte = get_request_info()
    return JsonResponse({"ip": ip, "agent": agent, "fonte": fonte})


urlpatterns = [
    path("async-middleware/", async_middleware_view, name="async-middleware"),
    path("configuracoes/", ConfiguracoesView.as_view(), name="configuracoes"),
    path("accounts/", include(("accounts.urls", "accounts"), namespace="accounts")),
    path("", include("Hubx.urls")),
]
