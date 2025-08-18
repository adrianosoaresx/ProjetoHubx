import os

import pytest
from datetime import timedelta
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import IntegrityError
from django.utils import timezone

from accounts.models import UserType
from nucleos.models import CoordenadorSuplente, Nucleo, ParticipacaoNucleo
from organizacoes.models import Organizacao

pytestmark = pytest.mark.django_db


@pytest.fixture
def media_root(tmp_path, settings):
    settings.MEDIA_ROOT = tmp_path
    return tmp_path


@pytest.fixture
def organizacao():
    return Organizacao.objects.create(nome="Org", cnpj="00.000.000/0001-00", slug="org")


@pytest.fixture
def usuario(organizacao):
    User = get_user_model()
    return User.objects.create_user(
        username="membro",
        email="membro@example.com",
        password="pass",
        user_type=UserType.NUCLEADO,
        organizacao=organizacao,
    )


def test_str_representation(organizacao):
    nucleo = Nucleo.objects.create(nome="Núcleo Alpha", slug="alpha", organizacao=organizacao)
    assert str(nucleo) == "Núcleo Alpha"


def test_create_with_required_fields(media_root, organizacao):
    avatar = SimpleUploadedFile("avatar.png", b"a", content_type="image/png")
    cover = SimpleUploadedFile("cover.jpg", b"b", content_type="image/jpeg")
    nucleo = Nucleo.objects.create(
        organizacao=organizacao,
        nome="Núcleo Teste",
        slug="teste",
        descricao="Desc",
        avatar=avatar,
        cover=cover,
    )
    assert nucleo.descricao == "Desc"
    assert nucleo.avatar.name.startswith("nucleos/avatars/")
    assert nucleo.cover.name.startswith("nucleos/capas/")
    assert os.path.exists(nucleo.avatar.path)
    assert os.path.exists(nucleo.cover.path)
    assert nucleo.ativo is True


def test_participacao_unique_constraint(organizacao, usuario):
    nucleo = Nucleo.objects.create(nome="N1", slug="n1", organizacao=organizacao)
    ParticipacaoNucleo.objects.create(user=usuario, nucleo=nucleo)
    with pytest.raises(IntegrityError):
        ParticipacaoNucleo.objects.create(user=usuario, nucleo=nucleo)


def test_membros_property(organizacao, usuario):
    nucleo = Nucleo.objects.create(nome="N", slug="n", organizacao=organizacao)
    ParticipacaoNucleo.objects.create(user=usuario, nucleo=nucleo, status="pendente")
    u2 = get_user_model().objects.create_user(
        username="u2", email="u2@example.com", password="pass", user_type=UserType.NUCLEADO, organizacao=organizacao
    )
    ParticipacaoNucleo.objects.create(user=u2, nucleo=nucleo, status="ativo")
    u3 = get_user_model().objects.create_user(
        username="u3", email="u3@example.com", password="pass", user_type=UserType.NUCLEADO, organizacao=organizacao
    )
    ParticipacaoNucleo.objects.create(
        user=u3, nucleo=nucleo, status="ativo", status_suspensao=True
    )
    assert list(nucleo.membros) == [u2]


def test_suplente_ativo(organizacao, usuario):
    nucleo = Nucleo.objects.create(nome="N", slug="n", organizacao=organizacao)
    ParticipacaoNucleo.objects.create(user=usuario, nucleo=nucleo, status="ativo")
    now = timezone.now()
    suplente = CoordenadorSuplente.objects.create(
        nucleo=nucleo,
        usuario=usuario,
        periodo_inicio=now - timedelta(days=1),
        periodo_fim=now + timedelta(days=1),
    )
    assert suplente.ativo


def test_slug_unico_por_organizacao(organizacao):
    outra = Organizacao.objects.create(nome="Org2", cnpj="11.111.111/0001-11", slug="org2")
    Nucleo.objects.create(nome="N1", slug="igual", organizacao=organizacao)
    Nucleo.objects.create(nome="N2", slug="igual", organizacao=outra)
    with pytest.raises(IntegrityError):
        Nucleo.objects.create(nome="N3", slug="igual", organizacao=organizacao)


@pytest.mark.xfail(reason="Arquivos não são removidos ao deletar o núcleo")
def test_upload_cleanup(media_root, organizacao):
    avatar = SimpleUploadedFile("a.png", b"a", content_type="image/png")
    cover = SimpleUploadedFile("c.jpg", b"c", content_type="image/jpeg")
    nucleo = Nucleo.objects.create(
        organizacao=organizacao,
        nome="Cleanup",
        slug="cleanup",
        avatar=avatar,
        cover=cover,
    )
    avatar_path, cover_path = nucleo.avatar.path, nucleo.cover.path
    nucleo.delete()
    assert not os.path.exists(avatar_path)
    assert not os.path.exists(cover_path)
