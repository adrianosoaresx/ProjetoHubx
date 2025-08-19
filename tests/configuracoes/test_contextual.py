import uuid  # required for uuid4 usage in tests

import pytest
from django.contrib.auth import get_user_model
from django.db import IntegrityError
from rest_framework.test import APIClient
from notificacoes.tasks import enviar_notificacao_async

from configuracoes.models import (
    ConfiguracaoContextual,
    ConfiguracaoContaLog,
)

User = get_user_model()

pytestmark = pytest.mark.django_db


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
    log = (
        ConfiguracaoContaLog.objects.filter(user=admin_user, campo="tema")
        .order_by("-created_at")
        .first()
    )
    assert log is not None
    assert log.valor_novo == "escuro"
    assert log.fonte == "import"


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
