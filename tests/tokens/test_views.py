import pyotp
import pytest
from django.urls import reverse
from django.utils import timezone

from accounts.factories import UserFactory
from nucleos.factories import NucleoFactory
from organizacoes.factories import OrganizacaoFactory
from tokens.models import CodigoAutenticacao, TokenAcesso, TOTPDevice

pytestmark = pytest.mark.django_db


def _login(client, user):
    client.force_login(user)


def test_criar_token_view_creates_token(client):
    user = UserFactory(is_staff=True)
    _login(client, user)
    resp = client.post(reverse("tokens:criar_token"), {"tipo_destino": TokenAcesso.TipoUsuario.ADMIN})
    assert resp.status_code == 200
    token = TokenAcesso.objects.get(gerado_por=user)
    assert token.tipo_destino == TokenAcesso.TipoUsuario.ADMIN
    assert token.gerado_por == user


def test_gerar_token_convite_view(client):
    user = UserFactory(is_staff=True)
    org = OrganizacaoFactory()
    org.users.add(user)
    nucleo = NucleoFactory(organizacao=org)
    _login(client, user)
    data = {
        "tipo_destino": TokenAcesso.TipoUsuario.CONVIDADO,
        "organizacao": org.pk,
        "nucleos": [nucleo.pk],
    }
    resp = client.post(reverse("tokens:gerar_convite"), data)
    assert resp.status_code == 200
    json = resp.json()
    token = TokenAcesso.objects.get(codigo=json["codigo"])
    assert token.data_expiracao.date() == (timezone.now() + timezone.timedelta(days=30)).date()


def test_validar_token_convite_view(client):
    user = UserFactory()
    gerador = UserFactory(is_staff=True)
    token = TokenAcesso.objects.create(gerado_por=gerador, tipo_destino=TokenAcesso.TipoUsuario.ASSOCIADO)

    _login(client, user)
    resp = client.post(reverse("tokens:validar_convite"), {"codigo": token.codigo})
    assert resp.status_code == 200
    token.refresh_from_db()
    assert token.estado == TokenAcesso.Estado.USADO
    assert token.usuario == user

    resp = client.post(reverse("tokens:validar_convite"), {"codigo": token.codigo})
    assert resp.status_code == 400


def test_gerar_codigo_autenticacao_view(client):
    user = UserFactory()
    _login(client, user)
    resp = client.post(reverse("tokens:gerar_codigo"), {"usuario": user.pk})
    assert resp.status_code == 200
    json = resp.json()
    assert "codigo" in json
    assert CodigoAutenticacao.objects.filter(usuario=user).exists()


def test_validar_codigo_autenticacao_view(client):
    user = UserFactory()
    _login(client, user)
    codigo = CodigoAutenticacao.objects.create(
        usuario=user, codigo="123456", expira_em=timezone.now() + timezone.timedelta(minutes=10)
    )
    resp = client.post(reverse("tokens:validar_codigo"), {"codigo": codigo.codigo})
    assert resp.status_code == 200
    codigo.refresh_from_db()
    assert codigo.verificado is True

    resp = client.post(reverse("tokens:validar_codigo"), {"codigo": "000000"})
    assert resp.status_code == 400


def test_ativar_e_desativar_2fa_views(client):
    user = UserFactory()
    _login(client, user)
    device = TOTPDevice.objects.create(usuario=user)
    totp = pyotp.TOTP(device.secret).now()
    resp = client.post(reverse("tokens:ativar_2fa"), {"codigo_totp": totp})
    assert resp.status_code == 200
    device.refresh_from_db()
    assert device.confirmado is True

    resp = client.post(reverse("tokens:desativar_2fa"))
    assert resp.status_code == 200
    assert not TOTPDevice.objects.filter(usuario=user).exists()
