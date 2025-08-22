import uuid  # required for uuid4 usage in tests

import pytest
from django.contrib.auth import get_user_model
from django.db import IntegrityError
from django.test import override_settings
from rest_framework.settings import api_settings
from rest_framework.test import APIClient
from notificacoes.tasks import enviar_notificacao_async

from configuracoes.models import (
    ConfiguracaoContextual,
    ConfiguracaoContaLog,
)
from organizacoes.factories import OrganizacaoFactory
from nucleos.factories import NucleoFactory
from agenda.factories import EventoFactory

User = get_user_model()

pytestmark = [pytest.mark.django_db, pytest.mark.urls("tests.configuracoes.urls")]


def test_contextual_unique_constraint(admin_user):
    escopo_id = uuid.uuid4()
    ConfiguracaoContextual.objects.create(
        user=admin_user,
        escopo_tipo="organizacao",
        escopo_id=escopo_id,
    )
    with pytest.raises(IntegrityError):
        ConfiguracaoContextual.objects.create(
            user=admin_user,
            escopo_tipo="organizacao",
            escopo_id=escopo_id,
        )


def test_signal_creates_log(admin_user):
    config = admin_user.configuracao
    config.tema = "escuro"
    config.save()
    log = ConfiguracaoContaLog.objects.filter(user=admin_user, campo="tema").order_by("-created_at").first()
    assert log is not None
    assert log.valor_novo == "escuro"
    assert log.fonte == "import"


def test_logs_created_for_push_fields(admin_user):
    config = ConfiguracaoContextual.objects.create(
        user=admin_user,
        escopo_tipo="organizacao",
        escopo_id=uuid.uuid4(),
    )
    config.receber_notificacoes_push = False
    config.frequencia_notificacoes_push = "diaria"
    config.save()
    log_receber = (
        ConfiguracaoContaLog.objects.filter(
            user=admin_user,
            campo="receber_notificacoes_push",
            valor_novo="False",
        )
        .order_by("-created_at")
        .first()
    )
    log_freq = (
        ConfiguracaoContaLog.objects.filter(
            user=admin_user,
            campo="frequencia_notificacoes_push",
            valor_novo="diaria",
        )
        .order_by("-created_at")
        .first()
    )
    assert log_receber is not None
    assert log_receber.valor_antigo == "True"
    assert log_receber.fonte == "import"
    assert log_freq is not None
    assert log_freq.valor_antigo == "imediata"
    assert log_freq.fonte == "import"


def test_endpoint_testar_notificacao(admin_user, monkeypatch):
    monkeypatch.setattr(enviar_notificacao_async, "delay", lambda *a, **k: None)
    client = APIClient()
    client.force_authenticate(user=admin_user)
    resp = client.post("/api/configuracoes/testar/", {"canal": "email"}, format="json")
    assert resp.status_code == 200


def test_endpoint_respeita_preferencias(admin_user, monkeypatch):
    monkeypatch.setattr(enviar_notificacao_async, "delay", lambda *a, **k: None)
    client = APIClient()
    client.force_authenticate(user=admin_user)
    admin_user.configuracao.receber_notificacoes_email = False
    admin_user.configuracao.save(update_fields=["receber_notificacoes_email"])
    resp = client.post("/api/configuracoes/testar/", {"canal": "email"}, format="json")
    assert resp.status_code == 400


@override_settings(
    CACHES={"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}
)
def test_testar_notificacao_throttling(admin_user, monkeypatch):
    monkeypatch.setattr(enviar_notificacao_async, "delay", lambda *a, **k: None)
    from configuracoes.throttles import TestarNotificacaoThrottle
    from django.core.cache import cache

    client = APIClient()
    client.force_authenticate(user=admin_user)
    cache.clear()
    url = "/api/configuracoes/testar/"
    original = api_settings.DEFAULT_THROTTLE_RATES.copy()
    api_settings.DEFAULT_THROTTLE_RATES["testar_notificacao"] = "5/minute"
    TestarNotificacaoThrottle.THROTTLE_RATES = api_settings.DEFAULT_THROTTLE_RATES
    try:
        for _ in range(5):
            resp = client.post(url, {"canal": "email"}, format="json")
            assert resp.status_code == 200
        resp = client.post(url, {"canal": "email"}, format="json")
        assert resp.status_code == 429
    finally:
        api_settings.DEFAULT_THROTTLE_RATES = original
        TestarNotificacaoThrottle.THROTTLE_RATES = api_settings.DEFAULT_THROTTLE_RATES
        cache.clear()


def test_escopo_nome_organizacao(admin_user):
    organizacao = OrganizacaoFactory()
    config = ConfiguracaoContextual.objects.create(
        user=admin_user,
        escopo_tipo="organizacao",
        escopo_id=organizacao.id,
    )
    assert config.escopo_nome == organizacao.nome


def test_escopo_nome_nucleo(admin_user):
    nucleo = NucleoFactory()
    config = ConfiguracaoContextual.objects.create(
        user=admin_user,
        escopo_tipo="nucleo",
        escopo_id=nucleo.id,
    )
    assert config.escopo_nome == nucleo.nome


def test_escopo_nome_evento(admin_user):
    evento = EventoFactory()
    config = ConfiguracaoContextual.objects.create(
        user=admin_user,
        escopo_tipo="evento",
        escopo_id=evento.id,
    )
    assert config.escopo_nome == evento.titulo
