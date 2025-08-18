import pytest

from accounts.factories import UserFactory
from configuracoes.models import ConfiguracaoConta
from configuracoes.services import atualizar_preferencias_usuario
from notificacoes.models import NotificationLog, NotificationTemplate
from notificacoes.services import notificacoes as svc

pytestmark = pytest.mark.django_db


def test_render_template() -> None:
    template = NotificationTemplate.objects.create(
        codigo="t", assunto="Oi {{ nome }}", corpo="C {{ valor }}", canal="email"
    )
    subject, body = svc.render_template(template, {"nome": "Ana", "valor": 10})
    assert subject == "Oi Ana"
    assert body == "C 10"


def test_enviar_para_usuario(monkeypatch) -> None:
    user = UserFactory()
    NotificationTemplate.objects.create(codigo="t", assunto="Oi", corpo="C", canal="email")
    called = {}

    def fake_delay(*args, **kwargs):
        called["count"] = called.get("count", 0) + 1

    monkeypatch.setattr(
        "notificacoes.services.notificacoes.enviar_notificacao_async.delay",
        fake_delay,
    )

    svc.enviar_para_usuario(user, "t", {})

    log = NotificationLog.objects.get()
    assert called.get("count") == 1
    assert log.status == "pendente"
    assert log.destinatario.startswith(user.email[:2])


def test_enviar_para_usuario_agrupado(monkeypatch) -> None:
    """Não envia imediatamente quando configurado para resumo diário."""
    user = UserFactory()
    NotificationTemplate.objects.create(codigo="t", assunto="Oi", corpo="C", canal="email")
    config = ConfiguracaoConta.objects.get(user=user)
    config.frequencia_notificacoes_email = "diaria"
    config.save(update_fields=["frequencia_notificacoes_email"])
    called = {}

    def fake_delay(*args, **kwargs):
        called["count"] = called.get("count", 0) + 1

    monkeypatch.setattr(
        "notificacoes.services.notificacoes.enviar_notificacao_async.delay",
        fake_delay,
    )

    svc.enviar_para_usuario(user, "t", {})

    log = NotificationLog.objects.get()
    assert called.get("count", 0) == 0
    assert log.status == "pendente"


def test_enviar_sem_canais() -> None:
    user = UserFactory()
    NotificationTemplate.objects.create(codigo="t", assunto="Oi", corpo="C", canal="email")
    atualizar_preferencias_usuario(user, {"receber_notificacoes_email": False})

    with pytest.raises(ValueError):
        svc.enviar_para_usuario(user, "t", {})
    assert NotificationLog.objects.count() == 0


def test_template_inexistente() -> None:
    user = UserFactory()
    with pytest.raises(ValueError):
        svc.enviar_para_usuario(user, "x", {})


def test_enviar_multiplos_canais(monkeypatch) -> None:
    user = UserFactory()
    NotificationTemplate.objects.create(codigo="t", assunto="Oi", corpo="C", canal="todos")
    config = ConfiguracaoConta.objects.get(user=user)
    config.receber_notificacoes_whatsapp = True
    config.save(update_fields=["receber_notificacoes_whatsapp"])
    called = {}

    def fake_delay(*args, **kwargs):
        called["count"] = called.get("count", 0) + 1

    monkeypatch.setattr(
        "notificacoes.services.notificacoes.enviar_notificacao_async.delay",
        fake_delay,
    )

    svc.enviar_para_usuario(user, "t", {})

    assert called.get("count") >= 1
    assert NotificationLog.objects.count() >= 1


def test_enviar_para_usuario_respeita_push(monkeypatch) -> None:
    user = UserFactory()
    NotificationTemplate.objects.create(codigo="p", assunto="Oi", corpo="C", canal="push")
    atualizar_preferencias_usuario(user, {"receber_notificacoes_push": False})
    called = {}

    def fake_delay(*args, **kwargs):
        called["count"] = called.get("count", 0) + 1

    monkeypatch.setattr(
        "notificacoes.services.notificacoes.enviar_notificacao_async.delay",
        fake_delay,
    )

    with pytest.raises(ValueError):
        svc.enviar_para_usuario(user, "p", {})
    assert called.get("count", 0) == 0
