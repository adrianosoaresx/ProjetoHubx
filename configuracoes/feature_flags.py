from __future__ import annotations

from django.contrib.auth import get_user_model

from configuracoes.models import ConfiguracaoChatOrganizacao, ConfiguracaoConta
from organizacoes.models import Organizacao

User = get_user_model()


def is_chat_enabled_for_organization(organizacao: Organizacao) -> bool:
    """Retorna se o chat está habilitado para a organização informada."""

    try:
        configuracao = organizacao.configuracao_chat
    except ConfiguracaoChatOrganizacao.DoesNotExist:
        return True
    return configuracao.chat_habilitado


def is_chat_enabled_for_user(user: User) -> bool:
    """Retorna se o chat está habilitado para o usuário informado."""

    try:
        configuracao = user.configuracao
    except ConfiguracaoConta.DoesNotExist:
        return True
    return configuracao.chat_habilitado
