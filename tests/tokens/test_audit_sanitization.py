import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from accounts.factories import UserFactory
from accounts.models import UserType
from audit.models import AuditLog
from tokens.models import TokenAcesso

pytestmark = pytest.mark.django_db


def test_audit_sanitization():
    issuer = UserFactory(user_type=UserType.NUCLEADO.value)
    client = APIClient()
    client.force_authenticate(user=issuer)
    url = reverse("tokens_api:token-list")
    resp = client.post(url, {"tipo_destino": TokenAcesso.TipoUsuario.CONVIDADO.value})
    assert resp.status_code == 403
    log = AuditLog.objects.latest("created_at")
    assert "codigo" not in log.metadata
    assert "token" not in log.metadata
