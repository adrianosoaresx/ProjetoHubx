import pytest
import hashlib
import pytest
import pyotp
from django.urls import reverse
from django.utils import timezone

from accounts.factories import UserFactory
from accounts.models import UserType
from nucleos.factories import NucleoFactory
from organizacoes.factories import OrganizacaoFactory

from tokens.models import CodigoAutenticacao, CodigoAutenticacaoLog, TokenAcesso, TokenUsoLog
from tokens.services import create_invite_token

from tokens.models import ApiToken, ApiTokenLog, CodigoAutenticacao, CodigoAutenticacaoLog, TokenAcesso

pytestmark = pytest.mark.django_db


def _login(client, user):
    client.force_login(user)


def test_gerar_convite_form_fields(client):
    user = UserFactory(is_staff=True, user_type=UserType.ADMIN.value)
    org = OrganizacaoFactory()
    org.users.add(user)
    NucleoFactory(organizacao=org)
    _login(client, user)
    resp = client.get(reverse("tokens:gerar_convite"))
    assert resp.status_code == 200
    content = resp.content.decode()
    assert "name=\"tipo_destino\"" in content
    assert "name=\"organizacao\"" in content
    assert "name=\"nucleos\"" in content


def test_gerar_token_convite_view(client):
    user = UserFactory(is_staff=True, user_type=UserType.ADMIN.value)
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
    assert json["codigo"]
    token = TokenAcesso.objects.get(gerado_por=user)
    assert token.data_expiracao.date() == (timezone.now() + timezone.timedelta(days=30)).date()


def test_convite_permission_denied(client):
    user = UserFactory(is_staff=True, user_type=UserType.ADMIN.value)
    org = OrganizacaoFactory()
    org.users.add(user)
    _login(client, user)
    resp = client.post(
        reverse("tokens:gerar_convite"),
        {"tipo_destino": TokenAcesso.TipoUsuario.ADMIN, "organizacao": org.pk},
    )
    assert resp.status_code == 403

def test_convite_permission_denied_no_side_effects(client):
    user = UserFactory(is_staff=True, user_type=UserType.ADMIN.value)
    org = OrganizacaoFactory()
    org.users.add(user)
    _login(client, user)
    assert TokenAcesso.objects.count() == 0
    assert TokenUsoLog.objects.count() == 0
    resp = client.post(
        reverse("tokens:gerar_convite"),
        {"tipo_destino": TokenAcesso.TipoUsuario.ADMIN, "organizacao": org.pk},
    )
    assert resp.status_code == 403
    assert TokenAcesso.objects.count() == 0
    assert TokenUsoLog.objects.count() == 0


def test_convite_daily_limit(client):
    user = UserFactory(is_staff=True, user_type=UserType.ADMIN.value)
    org = OrganizacaoFactory()
    org.users.add(user)
    _login(client, user)
    data = {"tipo_destino": TokenAcesso.TipoUsuario.CONVIDADO, "organizacao": org.pk}
    for _ in range(5):
        resp = client.post(reverse("tokens:gerar_convite"), data)
        assert resp.status_code == 200
    assert TokenAcesso.objects.count() == 5
    resp = client.post(reverse("tokens:gerar_convite"), data)
    assert resp.status_code == 429
    assert TokenAcesso.objects.count() == 5



def test_validar_token_convite_get(client):
    user = UserFactory()
    _login(client, user)
    resp = client.get(reverse("tokens:validar_token"))
    assert resp.status_code == 200


def test_validar_token_convite_view(client):
    user = UserFactory()
    gerador = UserFactory(is_staff=True)

    token = TokenAcesso(gerado_por=gerador, tipo_destino=TokenAcesso.TipoUsuario.ASSOCIADO)
    codigo = "a" * 32
    token.set_codigo(codigo)
    token.save()


    _login(client, user)
    resp = client.post(reverse("tokens:validar_token"), {"codigo": codigo})
    assert resp.status_code == 200
    token.refresh_from_db()
    assert token.estado == TokenAcesso.Estado.USADO
    assert token.usuario == user
    log = TokenUsoLog.objects.get(token=token)
    assert log.acao == TokenUsoLog.Acao.USO
    assert log.usuario == user

    resp = client.post(reverse("tokens:validar_token"), {"codigo": codigo})
    assert resp.status_code == 400


def test_gerar_codigo_autenticacao_view(client):
    user = UserFactory()
    _login(client, user)
    resp = client.post(
        reverse("tokens:gerar_codigo"),
        {},
        HTTP_USER_AGENT="ua-gerar",
    )
    assert resp.status_code == 200
    json = resp.json()
    assert "codigo" in json
    codigo_obj = CodigoAutenticacao.objects.get(usuario=user)
    log = CodigoAutenticacaoLog.objects.get(codigo=codigo_obj, acao="emissao")
    assert log.ip == "127.0.0.1"
    assert log.user_agent == "ua-gerar"


def test_gerar_codigo_autenticacao_get(client):
    user = UserFactory()
    _login(client, user)
    resp = client.get(reverse("tokens:gerar_codigo"))
    assert resp.status_code == 200


def test_validar_codigo_autenticacao_view(client):
    user = UserFactory()
    _login(client, user)
    codigo = CodigoAutenticacao(usuario=user)
    codigo.set_codigo("123456")
    codigo.expira_em = timezone.now() + timezone.timedelta(minutes=10)
    codigo.save()
    resp = client.post(
        reverse("tokens:validar_codigo"),
        {"codigo": codigo.codigo},
        HTTP_USER_AGENT="ua-validar",
    )
    assert resp.status_code == 200
    codigo.refresh_from_db()
    assert codigo.verificado is True
    log = CodigoAutenticacaoLog.objects.get(codigo=codigo, acao="validacao")
    assert log.ip == "127.0.0.1"
    assert log.user_agent == "ua-validar"

    resp = client.post(reverse("tokens:validar_codigo"), {"codigo": "000000"})
    assert resp.status_code == 400


def test_validar_codigo_autenticacao_get(client):
    user = UserFactory()
    _login(client, user)
    resp = client.get(reverse("tokens:validar_codigo"))
    assert resp.status_code == 200


def test_ativar_e_desativar_2fa_views(client):
    user = UserFactory()
    _login(client, user)
    resp = client.get(reverse("tokens:ativar_2fa"))
    assert resp.status_code == 200
    user.refresh_from_db()
    totp = pyotp.TOTP(user.two_factor_secret).now()
    resp = client.post(reverse("tokens:ativar_2fa"), {"codigo_totp": totp})
    assert resp.status_code == 302
    user.refresh_from_db()
    assert user.two_factor_enabled is True

    resp = client.post(reverse("tokens:desativar_2fa"))
    assert resp.status_code == 302
    user.refresh_from_db()
    assert user.two_factor_enabled is False and user.two_factor_secret is None


def test_gerar_api_token_view(client):
    user = UserFactory()
    _login(client, user)
    data = {"scope": "read", "client_name": "cli", "expires_in": 1}
    resp = client.post(
        reverse("tokens:gerar_api_token"),
        data,
        HTTP_USER_AGENT="ua-gen",
    )
    assert resp.status_code == 200
    json = resp.json()
    assert "token" in json
    token_hash = hashlib.sha256(json["token"].encode()).hexdigest()
    token = ApiToken.objects.get(token_hash=token_hash)
    assert token.user == user
    log = ApiTokenLog.objects.get(token=token, acao="geracao")
    assert log.user_agent == "ua-gen"
    assert log.ip == "127.0.0.1"
