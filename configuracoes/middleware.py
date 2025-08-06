from __future__ import annotations

from django.middleware.locale import LocaleMiddleware
from django.utils import translation

from configuracoes.services import get_configuracao_conta


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
