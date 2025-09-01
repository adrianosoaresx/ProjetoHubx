import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from accounts.factories import UserFactory
from accounts.models import UserType
from tokens.models import TokenAcesso

pytestmark = pytest.mark.django_db


@pytest.mark.parametrize(
    "issuer_type,target,expected",
    [
        (UserType.ROOT, TokenAcesso.TipoUsuario.ADMIN, status.HTTP_201_CREATED),
        (UserType.ROOT, TokenAcesso.TipoUsuario.ASSOCIADO, status.HTTP_403_FORBIDDEN),
        (UserType.ADMIN, TokenAcesso.TipoUsuario.CONVIDADO, status.HTTP_201_CREATED),
        (UserType.ADMIN, TokenAcesso.TipoUsuario.ADMIN, status.HTTP_403_FORBIDDEN),
        (UserType.COORDENADOR, TokenAcesso.TipoUsuario.CONVIDADO, status.HTTP_201_CREATED),
        (UserType.COORDENADOR, TokenAcesso.TipoUsuario.ASSOCIADO, status.HTTP_403_FORBIDDEN),
    ],
)
def test_issue_permissions(issuer_type, target, expected):
    user = UserFactory(user_type=issuer_type.value)
    client = APIClient()
    client.force_authenticate(user=user)
    url = reverse("tokens_api:token-list")
    resp = client.post(url, {"tipo_destino": target})
    assert resp.status_code == expected
