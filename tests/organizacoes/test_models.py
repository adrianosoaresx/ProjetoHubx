import os

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import IntegrityError
from organizacoes.models import Organizacao

pytestmark = pytest.mark.django_db


@pytest.fixture
def faker_ptbr():
    from faker import Faker

    return Faker("pt_BR")


@pytest.fixture
def media_root(tmp_path, settings):
    settings.MEDIA_ROOT = tmp_path
    return tmp_path


def test_str_representation(faker_ptbr):
    org = Organizacao.objects.create(
        nome="ONG Alpha",
        cnpj=faker_ptbr.cnpj(),
    )
    assert str(org) == "ONG Alpha"


def test_cnpj_unique_constraint(faker_ptbr):
    cnpj = faker_ptbr.cnpj()
    Organizacao.objects.create(
        nome=faker_ptbr.company(),
        cnpj=cnpj,
    )
    with pytest.raises(IntegrityError):
        Organizacao.objects.create(
            nome=faker_ptbr.company(),
            cnpj=cnpj,
        )


def test_file_upload_and_cleanup(media_root, faker_ptbr):
    avatar = SimpleUploadedFile("avatar.png", b"avatarcontent", content_type="image/png")
    cover = SimpleUploadedFile("cover.jpg", b"covercontent", content_type="image/jpeg")
    org = Organizacao.objects.create(
        nome=faker_ptbr.company(),
        cnpj=faker_ptbr.cnpj(),
        avatar=avatar,
        cover=cover,
    )
    assert org.avatar.name.startswith("organizacoes/avatars/")
    assert org.cover.name.startswith("organizacoes/capas/")
    assert os.path.exists(org.avatar.path)
    assert os.path.exists(org.cover.path)
    org.delete()
    # Arquivos permanecem após exclusão
    assert os.path.exists(os.path.join(media_root, org.avatar.name))
    assert os.path.exists(os.path.join(media_root, org.cover.name))


def test_ordering_by_nome(faker_ptbr):
    Organizacao.objects.create(nome="B", cnpj=faker_ptbr.cnpj())
    org_a = Organizacao.objects.create(nome="A", cnpj=faker_ptbr.cnpj())
    assert list(Organizacao.objects.all())[0] == org_a
