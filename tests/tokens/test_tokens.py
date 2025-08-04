import pyotp
import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse

from accounts.factories import UserFactory
from tokens.factories import TokenAcessoFactory
from tokens.forms import ValidarCodigoAutenticacaoForm, ValidarTokenConviteForm
from tokens.models import CodigoAutenticacao, TokenAcesso

User = get_user_model()

pytestmark = pytest.mark.django_db


@pytest.mark.django_db
def test_token_acesso_states():
    gerador = UserFactory(is_staff=True)
    token = TokenAcessoFactory(gerado_por=gerador, estado=TokenAcesso.Estado.NOVO)
    assert token.estado == TokenAcesso.Estado.NOVO
    token.estado = TokenAcesso.Estado.USADO
    token.save()
    assert TokenAcesso.objects.get(id=token.id).estado == TokenAcesso.Estado.USADO


@pytest.mark.django_db
def test_validar_token_convite_uso_unico():
    gerador = UserFactory(is_staff=True)
    usuario = UserFactory()
    token = TokenAcessoFactory(gerado_por=gerador, estado=TokenAcesso.Estado.NOVO)
    form = ValidarTokenConviteForm({"codigo": token.codigo})
    assert form.is_valid()
    form.token.usuario = usuario
    form.token.estado = TokenAcesso.Estado.USADO
    form.token.save()
    # tentativa de reutilizar
    form2 = ValidarTokenConviteForm({"codigo": token.codigo})
    assert not form2.is_valid()


@pytest.mark.django_db
def test_codigo_autenticacao_flow():
    usuario = UserFactory()
    codigo = CodigoAutenticacao(usuario=usuario)
    codigo.save()
    form = ValidarCodigoAutenticacaoForm({"codigo": codigo.codigo}, usuario=usuario)
    assert form.is_valid()
    codigo.refresh_from_db()
    assert codigo.verificado is True


@pytest.mark.django_db
def test_user_totp_generation():
    user = UserFactory(two_factor_secret=pyotp.random_base32())
    totp = pyotp.TOTP(user.two_factor_secret).now()
    assert len(totp) == 6


@pytest.mark.django_db
def test_view_permissions(client):
    url = reverse("tokens:gerar_convite")
    user = UserFactory()
    client.force_login(user)
    resp = client.post(url)
    assert resp.status_code in {400, 403, 302}
