import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from accounts.factories import UserFactory
from accounts.models import UserType
from organizacoes.factories import OrganizacaoFactory
from tokens import metrics as m
from tokens.models import TokenAcesso

pytestmark = pytest.mark.django_db


def reset_metrics():
    m.tokens_invites_created_total._value.set(0)
    m.tokens_invites_used_total._value.set(0)
    m.tokens_invites_revoked_total._value.set(0)
    m.tokens_validation_fail_total._value.set(0)
    m.tokens_rate_limited_total._value.set(0)
    m.tokens_webhooks_sent_total._value.set(0)
    m.tokens_webhooks_failed_total._value.set(0)
    m.tokens_webhook_latency_seconds._sum.set(0)


from django_redis import get_redis_connection


def test_metrics_flow():
    try:
        get_redis_connection("default").flushall()
    except Exception:
        from django.core.cache import cache

        cache.clear()
    reset_metrics()
    org = OrganizacaoFactory()
    user = UserFactory(user_type=UserType.ADMIN.value, organizacao=org)
    org.users.add(user)
    client = APIClient()
    client.force_authenticate(user=user)
    url = reverse("tokens_api:token-list")
    resp = client.post(url, {"tipo_destino": TokenAcesso.TipoUsuario.CONVIDADO.value})
    codigo = resp.data["codigo"]
    token_id = resp.data["id"]
    validate_url = reverse("tokens_api:token-validate") + f"?codigo={codigo}"
    client.get(validate_url)
    use_url = reverse("tokens_api:token-use", args=[token_id])
    client.post(use_url)
    revoke_url = reverse("tokens_api:token-revogar", kwargs={"codigo": codigo})
    client.post(revoke_url)
    client.get(validate_url)  # falha após revogação
    assert m.tokens_invites_created_total._value.get() == 1
    assert m.tokens_invites_used_total._value.get() == 1
    assert m.tokens_invites_revoked_total._value.get() == 1
    assert m.tokens_validation_fail_total._value.get() >= 1
    assert m.tokens_validation_latency_seconds._sum.get() > 0
