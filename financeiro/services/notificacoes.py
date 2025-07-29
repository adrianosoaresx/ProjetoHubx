from __future__ import annotations

"""Interface para o módulo de notificações do financeiro."""

from typing import Any


def enviar_cobranca(user: Any, lancamento: Any) -> None:
    """Envia notificação de cobrança a um usuário.

    Implementação futura integrará email, push e WhatsApp.
    """
    # TODO: integrar com módulo de notificações
    pass


def enviar_inadimplencia(user: Any, lancamento: Any) -> None:
    """Envia notificação de inadimplência a um usuário.

    Implementação futura integrará email, push e WhatsApp.
    """
    # TODO: integrar com módulo de notificações
    pass
