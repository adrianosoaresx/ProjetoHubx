from __future__ import annotations

from django.middleware.locale import LocaleMiddleware
from django.utils import translation
from contextvars import ContextVar
import asyncio

from configuracoes.services import get_configuracao_conta
from tokens.utils import get_client_ip

_local: ContextVar = ContextVar("request_info", default=None)


def get_request_info() -> tuple[str | None, str | None, str]:
    request = _local.get()
    if not request:
        return None, None, "import"
    fonte = "API" if request.path.startswith("/api/") else "UI"
    info = (
        get_client_ip(request),
        request.META.get("HTTP_USER_AGENT", ""),
        fonte,
    )
    _local.set(None)
    return info


class RequestInfoMiddleware:
    """Armazena informações da requisição em context vars para uso em sinais."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        token = _local.set(request)
        response = self.get_response(request)
        if asyncio.iscoroutine(response):

            async def _await_response():
                try:
                    return await response
                finally:
                    _local.reset(token)

            return _await_response()
        _local.reset(token)
        return response


class UserLocaleMiddleware(LocaleMiddleware):
    """Ativa o idioma considerando cookie ou preferências do usuário."""

    def process_request(self, request):  # type: ignore[override]
        response = super().process_request(request)
        lang = request.COOKIES.get("django_language")
        if lang:
            translation.activate(lang)
            request.LANGUAGE_CODE = translation.get_language()
            return response
        user = getattr(request, "user", None)
        if user and user.is_authenticated:
            config = get_configuracao_conta(user)
            translation.activate(config.idioma)
            request.LANGUAGE_CODE = translation.get_language()
        return response
