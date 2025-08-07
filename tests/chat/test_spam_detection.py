from __future__ import annotations

import pytest

from chat.models import ChatModerationLog
from chat.services import criar_canal, enviar_mensagem

pytestmark = pytest.mark.django_db


def test_repeated_messages_marked_as_spam(admin_user, coordenador_user):
    canal = criar_canal(
        criador=admin_user,
        contexto_tipo="privado",
        contexto_id=None,
        titulo="Privado",
        descricao="",
        participantes=[coordenador_user],
    )
    for _ in range(3):
        enviar_mensagem(canal, admin_user, "text", conteudo="spam")
    msg = enviar_mensagem(canal, admin_user, "text", conteudo="spam")
    assert msg.is_spam is True
    assert ChatModerationLog.objects.filter(message=msg, action="spam").exists()


def test_many_links_marked_as_spam(admin_user, coordenador_user):
    canal = criar_canal(
        criador=admin_user,
        contexto_tipo="privado",
        contexto_id=None,
        titulo="Privado",
        descricao="",
        participantes=[coordenador_user],
    )
    links = " ".join(
        [
            "http://example.com/a",
            "http://example.com/b",
            "http://example.com/c",
            "http://malicious.ru",
        ]
    )
    msg = enviar_mensagem(canal, admin_user, "text", conteudo=links)
    assert msg.is_spam is True
    assert ChatModerationLog.objects.filter(message=msg, action="spam").exists()
