from __future__ import annotations

"""Exceções específicas da camada de pagamento."""

from django.utils.translation import gettext_lazy as _


class PagamentoProviderError(RuntimeError):
    """Erro genérico retornado pelo provedor externo."""

    default_message = _("Erro ao processar pagamento com o provedor.")

    def __init__(self, message: str | None = None) -> None:
        super().__init__(message or self.default_message)


class PagamentoInvalidoError(ValueError):
    """Erro para dados de pagamento inválidos enviados pelo cliente."""

    default_message = _("Dados de pagamento inválidos.")

    def __init__(self, message: str | None = None) -> None:
        super().__init__(message or self.default_message)
