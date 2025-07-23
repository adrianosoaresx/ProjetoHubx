import os

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import IntegrityError
from django.utils.text import slugify

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
        slug="ong-alpha",
    )
    assert str(org) == "ONG Alpha"


def test_slug_uniqueness_and_slugified(faker_ptbr):
    name1 = faker_ptbr.company()
    name2 = faker_ptbr.company()
    org1 = Organizacao.objects.create(
        nome=name1,
        cnpj=faker_ptbr.cnpj(),
        slug=slugify(name1),
    )
    org2 = Organizacao.objects.create(
        nome=name2,
        cnpj=faker_ptbr.cnpj(),
        slug=slugify(name2),
    )
    assert org1.slug == slugify(name1)
    assert org2.slug == slugify(name2)
    assert org1.slug != org2.slug


def test_cnpj_unique_constraint(faker_ptbr):
    cnpj = faker_ptbr.cnpj()
    Organizacao.objects.create(
        nome=faker_ptbr.company(),
        cnpj=cnpj,
        slug="org-1",
    )
    with pytest.raises(IntegrityError):
        Organizacao.objects.create(
            nome=faker_ptbr.company(),
            cnpj=cnpj,
            slug="org-2",
        )


def test_file_upload_and_cleanup(media_root, faker_ptbr):
    avatar = SimpleUploadedFile("avatar.png", b"avatarcontent", content_type="image/png")
    cover = SimpleUploadedFile("cover.jpg", b"covercontent", content_type="image/jpeg")
    org = Organizacao.objects.create(
        nome=faker_ptbr.company(),
        cnpj=faker_ptbr.cnpj(),
        slug="org-files",
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
