import uuid

import uuid

import pytest
from django.contrib.auth import get_user_model
from django.db import IntegrityError
from django.urls import reverse
from rest_framework.test import APIClient
from notificacoes.tasks import enviar_notificacao_async

from configuracoes.models import (
    ConfiguracaoContextual,
    ConfiguracaoContaLog,
)
from configuracoes.services import get_user_preferences
from configuracoes import metrics

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


def test_crud_contextual_api(admin_user):
    client = APIClient()
    client.force_authenticate(user=admin_user)
    url = reverse("configuracoes_api:configuracoes-contextuais")
    data = {
        "escopo_tipo": "organizacao",
        "escopo_id": str(uuid.uuid4()),
        "frequencia_notificacoes_email": "diaria",
    }
    resp = client.post(url, data, format="json")
    assert resp.status_code == 201
    ctx_id = resp.data["id"]
    resp = client.get(url)
    assert len(resp.data) == 1
    detail = reverse("configuracoes_api:configuracoes-contextuais-detail", args=[ctx_id])
    resp = client.patch(detail, {"tema": "escuro"}, format="json")
    assert resp.status_code == 200
    resp = client.delete(detail)
    assert resp.status_code == 204


def test_get_user_preferences_cache(admin_user):
    metrics.config_cache_hits_total._value.set(0)
    metrics.config_cache_misses_total._value.set(0)
    prefs1 = get_user_preferences(admin_user)
    assert prefs1 is not None
    prefs2 = get_user_preferences(admin_user)
    assert prefs2 is not None
    assert metrics.config_cache_misses_total._value.get() >= 1
    assert metrics.config_cache_hits_total._value.get() >= 1


def test_permission_scope(admin_user):
    other = User.objects.create(username="outro", email="o@e.com")
    ctx = ConfiguracaoContextual.objects.create(
        user=admin_user,
        escopo_tipo="organizacao",
        escopo_id=uuid.uuid4(),
    )
    client = APIClient()
    client.force_authenticate(other)
    url = reverse(
        "configuracoes_api:configuracoes-contextuais-detail", args=[ctx.id]
    )
    resp = client.patch(url, {"tema": "escuro"}, format="json")
    assert resp.status_code == 403
