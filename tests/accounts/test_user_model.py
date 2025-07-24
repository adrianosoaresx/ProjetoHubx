import pytest
from django.contrib.auth import get_user_model

from accounts.models import ConfiguracaoDeConta
from nucleos.models import Nucleo, ParticipacaoNucleo
from organizacoes.models import Organizacao

pytestmark = pytest.mark.django_db


@pytest.fixture
def organizacao():
    return Organizacao.objects.create(nome="Org", cnpj="00.000.000/0001-99")


def test_email_and_cpf_unique(organizacao):
    User = get_user_model()
    User.objects.create_user(
        username="u1",
        email="u@example.com",
        password="pass",
        nome_completo="U One",
        cpf="000.000.000-00",
        organizacao=organizacao,
    )
    with pytest.raises(Exception):
        User.objects.create_user(
            username="u2",
            email="u@example.com",
            password="pass",
            nome_completo="U Two",
            cpf="111.111.111-11",
            organizacao=organizacao,
        )
    with pytest.raises(Exception):
        User.objects.create_user(
            username="u3",
            email="u3@example.com",
            password="pass",
            nome_completo="U Three",
            cpf="000.000.000-00",
            organizacao=organizacao,
        )


def test_configuracao_de_conta_auto_created(organizacao):
    User = get_user_model()
    user = User.objects.create_user(
        username="alpha",
        email="alpha@example.com",
        password="pass",
        nome_completo="Alpha",
        cpf="222.222.222-22",
        organizacao=organizacao,
    )
    assert ConfiguracaoDeConta.objects.filter(user=user).exists()


def test_tipo_usuario_coordenador(organizacao):
    User = get_user_model()
    user = User.objects.create_user(
        username="coord",
        email="coord@example.com",
        password="pass",
        nome_completo="Coord",
        cpf="333.333.333-33",
        organizacao=organizacao,
        is_associado=True,
    )
    nucleo = Nucleo.objects.create(nome="N", organizacao=organizacao)
    ParticipacaoNucleo.objects.create(user=user, nucleo=nucleo, is_coordenador=True)
    assert user.get_tipo_usuario() == "coordenador"
    assert user.is_coordenador_do(nucleo)
