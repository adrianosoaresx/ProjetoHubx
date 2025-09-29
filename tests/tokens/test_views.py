import pytest
import pyotp
from django.urls import reverse
from django.utils import timezone

from accounts.factories import UserFactory
from accounts.models import UserType
from organizacoes.factories import OrganizacaoFactory

from tokens.models import CodigoAutenticacao, CodigoAutenticacaoLog, TokenAcesso, TokenUsoLog

pytestmark = pytest.mark.django_db


def _login(client, user):
    client.force_login(user)


def test_gerar_convite_form_fields(client):
    user = UserFactory(is_staff=True, user_type=UserType.ADMIN.value)
    org = OrganizacaoFactory()
    org.users.add(user)
    _login(client, user)
    resp = client.get(reverse("tokens:gerar_convite"))
    assert resp.status_code == 200
    content = resp.content.decode()
    assert 'name="tipo_destino"' in content
    assert 'name="organizacao"' not in content
    assert 'name="nucleos"' not in content


def test_gerar_token_convite_view(client):
    user = UserFactory(is_staff=True, user_type=UserType.ADMIN.value)
    org = OrganizacaoFactory()
    org.users.add(user)
    _login(client, user)
    data = {
        "tipo_destino": TokenAcesso.TipoUsuario.CONVIDADO.value,
        "organizacao": org.pk,

    }
    resp = client.post(reverse("tokens:gerar_convite"), data, HTTP_HX_REQUEST="true")
    assert resp.status_code == 200
    content = resp.content.decode()
    assert "Token:" in content
    token = TokenAcesso.objects.get(gerado_por=user)
    assert token.data_expiracao.date() == (timezone.now() + timezone.timedelta(days=30)).date()
    assert token.organizacao == org


def test_convite_respeita_organizacao_do_usuario(client):
    user = UserFactory(is_staff=True, user_type=UserType.ADMIN.value)
    org = OrganizacaoFactory()
    outra_org = OrganizacaoFactory()
    org.users.add(user)
    _login(client, user)
    resp = client.post(
        reverse("tokens:gerar_convite"),
        {
            "tipo_destino": TokenAcesso.TipoUsuario.CONVIDADO.value,
            "organizacao": outra_org.pk,
        },
    )
    assert resp.status_code == 200
    token = TokenAcesso.objects.get(gerado_por=user)
    assert token.organizacao == org


def test_convite_permission_denied(client):
    user = UserFactory(is_staff=True, user_type=UserType.NUCLEADO.value)
    org = OrganizacaoFactory()
    org.users.add(user)
    _login(client, user)
    resp = client.post(
        reverse("tokens:gerar_convite"),
        {"tipo_destino": TokenAcesso.TipoUsuario.CONVIDADO.value},
    )
    assert resp.status_code == 403


def test_convite_permission_denied_no_side_effects(client):
    user = UserFactory(is_staff=True, user_type=UserType.NUCLEADO.value)
    org = OrganizacaoFactory()
    org.users.add(user)
    _login(client, user)
    assert TokenAcesso.objects.count() == 0
    assert TokenUsoLog.objects.count() == 0
    resp = client.post(
        reverse("tokens:gerar_convite"),
        {"tipo_destino": TokenAcesso.TipoUsuario.CONVIDADO.value},
    )
    assert resp.status_code == 403
    assert TokenAcesso.objects.count() == 0
    assert TokenUsoLog.objects.count() == 0


def test_convite_daily_limit(client):
    user = UserFactory(is_staff=True, user_type=UserType.ADMIN.value)
    org = OrganizacaoFactory()
    org.users.add(user)
    _login(client, user)
    data = {"tipo_destino": TokenAcesso.TipoUsuario.CONVIDADO.value}
    for _ in range(5):
        resp = client.post(reverse("tokens:gerar_convite"), data)
        assert resp.status_code == 200
    assert TokenAcesso.objects.count() == 5
    resp = client.post(reverse("tokens:gerar_convite"), data)
    assert resp.status_code == 429
    assert TokenAcesso.objects.count() == 5



def test_gerar_codigo_autenticacao_view(client, monkeypatch):
    user = UserFactory()
    _login(client, user)
    monkeypatch.setattr("notificacoes.services.email_client.send_email", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        "notificacoes.services.whatsapp_client.send_whatsapp",
        lambda *args, **kwargs: None,
    )
    resp = client.post(
        reverse("tokens:gerar_codigo"),
        {},
        HTTP_USER_AGENT="ua-gerar",
        HTTP_HX_REQUEST="true",
    )
    assert resp.status_code == 200
    assert "Código gerado" in resp.content.decode()
    codigo_obj = CodigoAutenticacao.objects.get(usuario=user)
    log = CodigoAutenticacaoLog.objects.get(codigo=codigo_obj, acao="emissao")
    assert log.ip == "127.0.0.1"
    assert log.user_agent == "ua-gerar"
    assert log.status_envio == CodigoAutenticacaoLog.StatusEnvio.SUCESSO


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


def test_validar_codigo_autenticacao_view_invalido_log(client):
    user = UserFactory()
    _login(client, user)
    codigo = CodigoAutenticacao(usuario=user)
    codigo.set_codigo("123456")
    codigo.expira_em = timezone.now() - timezone.timedelta(minutes=1)
    codigo.save()
    resp = client.post(
        reverse("tokens:validar_codigo"),
        {"codigo": "123456"},
        HTTP_USER_AGENT="ua-invalid",
    )
    assert resp.status_code == 400
    codigo.refresh_from_db()
    assert codigo.tentativas == 1
    log = CodigoAutenticacaoLog.objects.get(codigo=codigo, acao="validacao")
    assert log.ip == "127.0.0.1"
    assert log.user_agent == "ua-invalid"


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

