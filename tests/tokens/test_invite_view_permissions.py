import pytest
from django.urls import reverse

from accounts.factories import UserFactory
from accounts.models import UserType
from organizacoes.factories import OrganizacaoFactory
from tokens.models import TokenAcesso

pytestmark = pytest.mark.django_db


def _login(client, user):
    client.force_login(user)


@pytest.mark.parametrize(
    "issuer_type,allowed",
    [
        (UserType.ROOT, [TokenAcesso.TipoUsuario.ADMIN]),
        (
            UserType.ADMIN,
            [
                TokenAcesso.TipoUsuario.COORDENADOR,
                TokenAcesso.TipoUsuario.NUCLEADO,
                TokenAcesso.TipoUsuario.ASSOCIADO,
                TokenAcesso.TipoUsuario.CONVIDADO,
            ],
        ),
        (UserType.COORDENADOR, [TokenAcesso.TipoUsuario.CONVIDADO]),
        (UserType.FINANCEIRO, []),
        (UserType.NUCLEADO, []),
        (UserType.ASSOCIADO, []),
        (UserType.CONVIDADO, []),
    ],
)
def test_get_permissions(client, issuer_type, allowed):
    user = UserFactory(user_type=issuer_type.value)
    org = OrganizacaoFactory()
    org.users.add(user)
    _login(client, user)
    resp = client.get(reverse("tokens:gerar_convite"))
    if allowed:
        assert resp.status_code == 200
        content = resp.content.decode()
        for role in allowed:
            assert f'value="{role}"' in content
    else:
        assert resp.status_code == 302
        assert resp.url == reverse("accounts:perfil")


@pytest.mark.parametrize(
    "issuer_type,target,expected",
    [
        (UserType.ROOT, TokenAcesso.TipoUsuario.ADMIN, 200),
        (UserType.ROOT, TokenAcesso.TipoUsuario.CONVIDADO, 403),
        (UserType.ADMIN, TokenAcesso.TipoUsuario.CONVIDADO, 200),
        (UserType.ADMIN, TokenAcesso.TipoUsuario.ADMIN, 403),
        (UserType.COORDENADOR, TokenAcesso.TipoUsuario.CONVIDADO, 200),
        (UserType.COORDENADOR, TokenAcesso.TipoUsuario.ASSOCIADO, 403),
        (UserType.FINANCEIRO, TokenAcesso.TipoUsuario.CONVIDADO, 403),
        (UserType.NUCLEADO, TokenAcesso.TipoUsuario.CONVIDADO, 403),
        (UserType.ASSOCIADO, TokenAcesso.TipoUsuario.CONVIDADO, 403),
        (UserType.CONVIDADO, TokenAcesso.TipoUsuario.CONVIDADO, 403),
    ],
)
def test_post_permissions(client, issuer_type, target, expected):
    user = UserFactory(user_type=issuer_type.value)
    org = OrganizacaoFactory()
    org.users.add(user)
    _login(client, user)
    data = {"tipo_destino": target, "organizacao": org.pk}
    resp = client.post(reverse("tokens:gerar_convite"), data)
    assert resp.status_code == expected
    if expected == 200:
        assert TokenAcesso.objects.filter(gerado_por=user, tipo_destino=target).exists()
    else:
        assert not TokenAcesso.objects.filter(gerado_por=user).exists()
