import pytest

from accounts.factories import UserFactory
from notificacoes.models import NotificationLog, NotificationTemplate
from notificacoes.services.notificacoes import enviar_para_usuario


pytestmark = pytest.mark.django_db


def test_chamada_por_modulo_externo(monkeypatch):
    user = UserFactory()
    NotificationTemplate.objects.create(codigo="fin", assunto="Oi", corpo="C", canal="email")
    called = {}

    def fake_delay(*args, **kwargs):
        called["count"] = called.get("count", 0) + 1

    monkeypatch.setattr(
        "notificacoes.services.notificacoes.enviar_notificacao_async.delay",
        fake_delay,
    )

    enviar_para_usuario(user, "fin", {})

    assert called.get("count") == 1
    assert NotificationLog.objects.count() == 1

