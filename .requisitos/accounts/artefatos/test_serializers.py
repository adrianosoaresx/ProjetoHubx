import pytest
from accounts.serializers import (
    UserSerializer,
    ConfiguracaoContaSerializer,
    ParticipacaoNucleoSerializer,
    ChangePasswordSerializer
)
from accounts.models import User, ConfiguracaoConta, ParticipacaoNucleo
from nucleos.models import Nucleo


pytestmark = pytest.mark.django_db


def test_user_serializer_render(user_factory):
    user = user_factory()
    serializer = UserSerializer(user)
    assert serializer.data["email"] == user.email
    assert "cpf" in serializer.data


def test_configuracao_serializer_update(user_factory):
    user = user_factory()
    conf = ConfiguracaoConta.objects.create(user=user, tema_escuro=False)
    data = {"tema_escuro": True}
    serializer = ConfiguracaoContaSerializer(conf, data=data, partial=True)
    assert serializer.is_valid()
    conf_atualizado = serializer.save()
    assert conf_atualizado.tema_escuro is True


def test_participacao_serializer_labels(user_factory, db):
    user = user_factory()
    nucleo = Nucleo.objects.create(nome="Tecnologia", organizacao=user.organizacao)
    participacao = ParticipacaoNucleo.objects.create(user=user, nucleo=nucleo, is_coordenador=True)
    serializer = ParticipacaoNucleoSerializer(participacao)
    assert serializer.data["nome_nucleo"] == "Tecnologia"
    assert serializer.data["is_coordenador"] is True


def test_change_password_serializer_valida():
    data = {"senha_atual": "senhaantiga", "nova_senha": "NovaSegura123!"}
    serializer = ChangePasswordSerializer(data=data)
    assert serializer.is_valid()
    assert serializer.validated_data["nova_senha"] == "NovaSegura123!"
