import pytest
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile

from accounts.factories import UserFactory
from accounts.models import UserType
from empresas.factories import EmpresaFactory


@pytest.mark.django_db
def test_admin_list_empresas_cards(client, settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path
    admin = UserFactory(user_type=UserType.ADMIN)
    admin.organizacao = admin.nucleo.organizacao
    admin.save()

    owner = UserFactory(organizacao=admin.organizacao)
    owner.avatar = SimpleUploadedFile("a.png", b"a", content_type="image/png")
    owner.save()

    empresa = EmpresaFactory(organizacao=admin.organizacao, usuario=owner, nome="Empresa X")
    EmpresaFactory()  # Empresa de outra organização

    client.force_login(admin)
    url = reverse("empresas:lista")
    resp = client.get(url, {"q": "Empresa X"})
    content = resp.content.decode()
    assert "Empresa X" in content
    assert owner.username in content
    assert reverse("empresas:detail", args=[empresa.pk]) in content
    assert "<img" in content
