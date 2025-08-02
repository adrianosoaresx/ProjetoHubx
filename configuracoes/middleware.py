from __future__ import annotations

from django.middleware.locale import LocaleMiddleware
from django.utils import translation

from configuracoes.services import get_configuracao_conta


class UserLocaleMiddleware(LocaleMiddleware):
    """Ativa o idioma salvo em ConfiguracaoConta para usuários autenticados."""

    def process_request(self, request):  # type: ignore[override]
        response = super().process_request(request)
        user = getattr(request, "user", None)
        if user and user.is_authenticated:
            config = get_configuracao_conta(user)
            translation.activate(config.idioma)
            request.LANGUAGE_CODE = translation.get_language()
        return response
