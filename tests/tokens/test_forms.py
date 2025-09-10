import pytest

pytestmark = pytest.mark.skip(reason="legacy tests")
import pytest
from django.utils import timezone

from django.core.exceptions import PermissionDenied

from accounts.factories import UserFactory
from nucleos.factories import NucleoFactory
from organizacoes.factories import OrganizacaoFactory
from tokens.forms import (
    Ativar2FAForm,
    GerarCodigoAutenticacaoAdminForm,
    GerarCodigoAutenticacaoForm,
    GerarTokenConviteForm,
    TokenAcessoForm,
    ValidarCodigoAutenticacaoForm,
    ValidarTokenConviteForm,
)
from tokens.models import CodigoAutenticacao, TokenAcesso

pytestmark = pytest.mark.django_db


def test_token_acesso_form_choices():
    form = TokenAcessoForm()
    choices = [c[0] for c in form.fields["tipo_destino"].choices]
    for choice in TokenAcesso.TipoUsuario.values:
        assert choice in choices


def test_gerar_token_convite_form_querysets():
    user = UserFactory(is_staff=True)
    org1 = OrganizacaoFactory()
    org1.users.add(user)
    nucleo1 = NucleoFactory(organizacao=org1)
    form = GerarTokenConviteForm(user=user)
    assert list(form.fields["organizacao"].queryset) == [org1]
    assert list(form.fields["nucleos"].queryset) == [nucleo1]


def test_validar_token_convite_form_errors():
    form = ValidarTokenConviteForm({"codigo": "naoexiste"})
    assert not form.is_valid()
    assert "Token inválido" in form.errors["codigo"][0]

    user = UserFactory(is_staff=True)
    token = TokenAcesso.objects.create(
        gerado_por=user,
        tipo_destino=TokenAcesso.TipoUsuario.ADMIN,
        data_expiracao=timezone.now() - timezone.timedelta(days=1),
    )
    form = ValidarTokenConviteForm({"codigo": token.codigo})
    assert not form.is_valid()
    assert "Token expirado" in form.errors["codigo"][0]


def test_validar_token_convite_form_success():
    user = UserFactory(is_staff=True)
    token = TokenAcesso.objects.create(gerado_por=user, tipo_destino=TokenAcesso.TipoUsuario.ADMIN)
    form = ValidarTokenConviteForm({"codigo": token.codigo})
    assert form.is_valid()
    assert form.token == token


def test_gerar_codigo_autenticacao_form_save():
    user = UserFactory()
    form = GerarCodigoAutenticacaoForm({}, usuario=user)
    assert form.is_valid()
    codigo = form.save()
    assert codigo.usuario == user
    assert codigo.codigo.isdigit() and len(codigo.codigo) == 6


def test_gerar_codigo_autenticacao_admin_form_permission():
    sem_perm = UserFactory()
    target = UserFactory()
    with pytest.raises(PermissionDenied):
        GerarCodigoAutenticacaoAdminForm({"usuario": target.pk}, user=sem_perm)
    admin = UserFactory(is_superuser=True)
    form = GerarCodigoAutenticacaoAdminForm({"usuario": target.pk}, user=admin)
    assert form.is_valid()
    codigo = form.save()
    assert codigo.usuario == target


def test_validar_codigo_autenticacao_form_flow():
    user = UserFactory()
    codigo = CodigoAutenticacao(usuario=user)
    codigo.set_codigo("123456")
    codigo.expira_em = timezone.now() + timezone.timedelta(minutes=10)
    codigo.save()

    form_wrong = ValidarCodigoAutenticacaoForm({"codigo": "000000"}, usuario=user)
    assert not form_wrong.is_valid()
    codigo.refresh_from_db()
    assert codigo.tentativas == 1

    form_right = ValidarCodigoAutenticacaoForm({"codigo": codigo.codigo}, usuario=user)
    assert form_right.is_valid()
    codigo.refresh_from_db()
    assert codigo.verificado is True

    # terceira tentativa após já verificado não deve alterar
    form_again = ValidarCodigoAutenticacaoForm({"codigo": "000000"}, usuario=user)
    assert not form_again.is_valid()


def test_validar_codigo_autenticacao_form_expirado_bloqueado():
    user = UserFactory()
    codigo = CodigoAutenticacao.objects.create(usuario=user)
    codigo.expira_em = timezone.now() - timezone.timedelta(seconds=1)
    codigo.set_codigo("654321")
    codigo.save(update_fields=["expira_em", "codigo_hash", "codigo_salt"])
    form = ValidarCodigoAutenticacaoForm({"codigo": codigo.codigo}, usuario=user)
    assert not form.is_valid()
    assert "expirado" in form.errors["codigo"][0]

    codigo = CodigoAutenticacao.objects.create(usuario=user)
    codigo.expira_em = timezone.now() + timezone.timedelta(minutes=10)
    codigo.set_codigo("222222")
    codigo.save(update_fields=["expira_em", "codigo_hash", "codigo_salt"])
    for _ in range(4):
        form = ValidarCodigoAutenticacaoForm({"codigo": "000000"}, usuario=user)
        assert not form.is_valid()
    assert "bloqueado" in form.errors["codigo"][0]


def test_ativar_2fa_form():
    user = UserFactory(two_factor_secret=pyotp.random_base32())
    totp_code = pyotp.TOTP(user.two_factor_secret).now()
    form = Ativar2FAForm({"codigo_totp": totp_code}, user=user)
    assert form.is_valid()
