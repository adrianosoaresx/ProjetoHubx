import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from accounts.factories import UserFactory
from organizacoes.factories import OrganizacaoFactory
from accounts.models import UserType
from tokens.models import TokenAcesso

pytestmark = pytest.mark.django_db


@pytest.mark.parametrize(
    "issuer_type,target,expected",
    [
        (UserType.ROOT, TokenAcesso.TipoUsuario.CONVIDADO, status.HTTP_201_CREATED),
        (UserType.ROOT, TokenAcesso.TipoUsuario.ASSOCIADO, status.HTTP_400_BAD_REQUEST),
        (UserType.ADMIN, TokenAcesso.TipoUsuario.CONVIDADO, status.HTTP_201_CREATED),
        (UserType.ADMIN, TokenAcesso.TipoUsuario.ASSOCIADO, status.HTTP_400_BAD_REQUEST),
        (UserType.COORDENADOR, TokenAcesso.TipoUsuario.CONVIDADO, status.HTTP_201_CREATED),
        (UserType.COORDENADOR, TokenAcesso.TipoUsuario.ASSOCIADO, status.HTTP_400_BAD_REQUEST),
    ],
)
def test_issue_permissions(issuer_type, target, expected):
    user = UserFactory(user_type=issuer_type.value, organizacao=OrganizacaoFactory())
    client = APIClient()
    client.force_authenticate(user=user)
    url = reverse("tokens_api:token-list")
    resp = client.post(url, {"tipo_destino": target.value})
    assert resp.status_code == expected
