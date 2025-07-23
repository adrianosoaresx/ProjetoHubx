import pytest
from django.utils import timezone

from accounts.factories import UserFactory
from tokens.models import CodigoAutenticacao, TokenAcesso, TOTPDevice

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


def test_totp_device_creation_and_totp():
    user = UserFactory()
    device = TOTPDevice(usuario=user)
    device.save()
    assert device.secret
    totp = device.gerar_totp()
    assert totp.isdigit() and len(totp) == 6


def test_totp_device_confirmacao():
    user = UserFactory()
    device = TOTPDevice.objects.create(usuario=user)
    assert device.confirmado is False
    device.confirmado = True
    device.save()
    device.refresh_from_db()
    assert device.confirmado is True
