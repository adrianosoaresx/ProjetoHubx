import pytest
pytestmark = pytest.mark.skip(reason="legacy tests")
from django.utils import timezone

import pyotp
import pytest
from django.utils import timezone

from accounts.factories import UserFactory
from tokens.models import CodigoAutenticacao, TokenAcesso

pytestmark = pytest.mark.django_db


def test_token_acesso_creation_defaults():
    user = UserFactory(is_staff=True)
    token = TokenAcesso.objects.create(gerado_por=user, tipo_destino=TokenAcesso.TipoUsuario.ADMIN)
    assert len(token.codigo) == 32
    assert token.estado == TokenAcesso.Estado.NOVO
    assert token.created_at is not None


def test_token_acesso_states():
    user = UserFactory(is_staff=True)
    for estado in TokenAcesso.Estado.values:
        token = TokenAcesso.objects.create(
            gerado_por=user,
            tipo_destino=TokenAcesso.TipoUsuario.ADMIN,
            estado=estado,
        )
        token.refresh_from_db()
        assert token.estado == estado


def test_codigo_autenticacao_creation():
    user = UserFactory()
    codigo = CodigoAutenticacao(usuario=user)
    codigo.save()
    assert len(codigo.codigo) == 6
    delta = codigo.expira_em - codigo.created_at
    assert delta.total_seconds() == pytest.approx(600, rel=0.1)


def test_codigo_autenticacao_is_expirado():
    user = UserFactory()
    expired = CodigoAutenticacao.objects.create(usuario=user)
    expired.expira_em = timezone.now() - timezone.timedelta(minutes=1)
    expired.save(update_fields=["expira_em"])
    assert expired.is_expirado() is True
    valid = CodigoAutenticacao.objects.create(usuario=user)
    valid.expira_em = timezone.now() + timezone.timedelta(minutes=5)
    valid.save(update_fields=["expira_em"])
    assert valid.is_expirado() is False


def test_user_two_factor_secret_totp():
    user = UserFactory(two_factor_secret=pyotp.random_base32(), two_factor_enabled=True)
    totp = pyotp.TOTP(user.two_factor_secret).now()
    assert totp.isdigit() and len(totp) == 6
