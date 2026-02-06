from __future__ import annotations

import asyncio
import logging
from contextvars import ContextVar

from django.conf import settings
from django.middleware.locale import LocaleMiddleware
from django.utils import translation
from django.utils.translation import check_for_language

from configuracoes.services import get_configuracao_conta
from tokens.utils import get_client_ip

_local: ContextVar = ContextVar("request_info", default=None)
logger = logging.getLogger(__name__)


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

        accepted_languages = {
            code.replace("_", "-").lower() for code, _ in settings.LANGUAGES
        }

        def _normalize_language_code(language_code: str | None) -> str | None:
            if not language_code:
                return None
            return language_code.replace("_", "-").lower()

        source = "default"
        lang = _normalize_language_code(request.COOKIES.get("django_language"))

        user = getattr(request, "user", None)
        if user and user.is_authenticated:
            config = get_configuracao_conta(user)
            user_lang = _normalize_language_code(config.idioma)
            if user_lang:
                lang = user_lang
                source = "user_config"
            elif lang:
                source = "cookie"
        elif lang:
            source = "cookie"

        if not lang:
            lang = _normalize_language_code(settings.LANGUAGE_CODE)
            source = "default"

        is_lang_accepted = bool(lang and lang in accepted_languages)
        if not is_lang_accepted or not check_for_language(lang):
            lang = _normalize_language_code(settings.LANGUAGE_CODE)
            source = "default"

        translation.activate(lang)
        request.LANGUAGE_CODE = translation.get_language()
        logger.debug(
            "Idioma aplicado na requisição: %s (fonte=%s)",
            request.LANGUAGE_CODE,
            source,
        )

        return response
