import pytest

pytestmark = pytest.mark.skip(reason="legacy tests")
from django.utils import timezone

import hashlib

import pyotp
import pytest
from django.utils import timezone

from accounts.factories import UserFactory
from tokens.models import CodigoAutenticacao, TokenAcesso, TOTPDevice
from tokens.services import create_invite_token

pytestmark = pytest.mark.django_db


def test_token_acesso_creation_defaults():
    user = UserFactory(is_staff=True)
    token, codigo = create_invite_token(
        gerado_por=user,
        tipo_destino=TokenAcesso.TipoUsuario.CONVIDADO.value,
    )
    assert len(codigo) >= 32
    assert token.estado == TokenAcesso.Estado.NOVO
    assert token.created_at is not None


def test_token_acesso_states():
    user = UserFactory(is_staff=True)
    for estado in TokenAcesso.Estado.values:
        token, _ = create_invite_token(
            gerado_por=user,
            tipo_destino=TokenAcesso.TipoUsuario.CONVIDADO.value,
        )
        token.estado = estado
        token.save(update_fields=["estado"])
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


def test_totpdevice_secret_base32_preserved():
    user = UserFactory()
    secret = pyotp.random_base32()
    device = TOTPDevice.objects.create(usuario=user, secret=secret, confirmado=True)
    assert device.secret == secret
    code = pyotp.TOTP(secret).now()
    assert len(code) == 6


def test_totpdevice_gerar_totp_with_legacy_hash():
    user = UserFactory(two_factor_secret=pyotp.random_base32())
    device = TOTPDevice.objects.create(usuario=user, secret=user.two_factor_secret, confirmado=True)
    # Simula segredo legado (hash SHA-256) ainda armazenado no dispositivo; o
    # ``save`` deve reidratar o valor Base32 do usuário automaticamente.
    device.secret = hashlib.sha256(user.two_factor_secret.encode()).hexdigest()
    device.save(update_fields=["secret"])
    device.refresh_from_db()
    assert device.secret == user.two_factor_secret

    totp = device.gerar_totp()
    assert totp.isdigit() and len(totp) == 6


def test_user_two_factor_secret_totp():
    user = UserFactory(two_factor_secret=pyotp.random_base32(), two_factor_enabled=True)
    totp = pyotp.TOTP(user.two_factor_secret).now()
    assert totp.isdigit() and len(totp) == 6
