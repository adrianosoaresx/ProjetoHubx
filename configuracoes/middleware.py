from __future__ import annotations

from django.middleware.locale import LocaleMiddleware
from django.utils import translation
import threading

from configuracoes.services import get_configuracao_conta

_local = threading.local()


def get_request_info() -> tuple[str | None, str | None, str]:
    request = getattr(_local, "request", None)
    if not request:
        return None, None, "import"
    fonte = "API" if request.path.startswith("/api/") else "UI"
    return (
        request.META.get("REMOTE_ADDR"),
        request.META.get("HTTP_USER_AGENT", ""),
        fonte,
    )


class RequestInfoMiddleware:
    """Armazena informações da requisição em thread local para uso em sinais."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        _local.request = request
        return self.get_response(request)


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
