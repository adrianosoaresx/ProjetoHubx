from urllib.parse import urlencode

import pytest
from django.urls import reverse
from django.utils import timezone

from eventos.factories import EventoFactory
from eventos.models import PreRegistroConvite
from tokens.factories import TokenAcessoFactory
from tokens.models import TokenAcesso


pytestmark = pytest.mark.django_db


def _build_preregistro(email="guest@example.com"):
    evento = EventoFactory()
    token = TokenAcessoFactory(
        estado=TokenAcesso.Estado.NOVO,
        data_expiracao=timezone.now() + timezone.timedelta(hours=1),
        tipo_destino=TokenAcesso.TipoUsuario.CONVIDADO.value,
        organizacao=evento.organizacao,
    )
    preregistro = PreRegistroConvite.objects.create(
        email=email,
        evento=evento,
        codigo="CONFIRM123",
        token=token,
        status=PreRegistroConvite.Status.ENVIADO,
    )
    return preregistro, evento


def test_confirmar_convite_redireciona_com_parametros(client):
    preregistro, evento = _build_preregistro()

    resp = client.get(
        reverse("accounts:confirmar_convite"),
        {"token": preregistro.codigo, "email": preregistro.email},
    )

    expected_url = f"{reverse('tokens:token')}?{urlencode({'token': preregistro.codigo, 'email': preregistro.email})}"
    assert resp.status_code == 302
    assert resp.url == expected_url

    session = client.session
    assert session["invite_token"] == preregistro.codigo
    assert session["email"] == preregistro.email
    assert session["invite_email"] == preregistro.email
    assert session["invite_event_id"] == str(evento.pk)


def test_confirmar_convite_invalido_nao_preenche_sessao(client):
    preregistro, _ = _build_preregistro()
    preregistro.token.estado = TokenAcesso.Estado.USADO
    preregistro.token.save(update_fields=["estado"])

    resp = client.get(
        reverse("accounts:confirmar_convite"),
        {"token": preregistro.codigo, "email": preregistro.email},
    )

    assert resp.status_code == 302
    assert resp.url == reverse("tokens:token")
    assert "invite_token" not in client.session


def test_email_form_prefilled_and_readonly_when_locked(client):
    session = client.session
    session["email"] = "locked@example.com"
    session["invite_email"] = "locked@example.com"
    session.save()

    resp = client.get(reverse("accounts:email"))

    assert resp.status_code == 200
    content = resp.content.decode()
    assert 'value="locked@example.com"' in content
    assert "readonly=\"readonly\"" in content


def test_email_form_rejects_changes_when_locked(client):
    session = client.session
    session["email"] = "locked@example.com"
    session["invite_email"] = "locked@example.com"
    session.save()

    resp = client.post(
        reverse("accounts:email"),
        {"email": "other@example.com"},
        follow=True,
    )

    assert resp.request["PATH_INFO"] == reverse("accounts:email")
    assert "O e-mail confirmado não pode ser alterado" in resp.content.decode()
    assert client.session["email"] == "locked@example.com"
