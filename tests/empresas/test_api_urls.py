import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from empresas.factories import EmpresaFactory


@pytest.fixture
def api_client():
    return APIClient()


@pytest.mark.django_db
def test_tag_list_endpoint(api_client, admin_user, tag_factory):
    api_client.force_authenticate(user=admin_user)
    tag_factory(nome="servico", categoria="serv")
    url = reverse("empresas_api:tag-list")
    resp = api_client.get(url)
    assert resp.status_code == 200


@pytest.mark.django_db
def test_contato_list_endpoint(api_client, admin_user):
    empresa = EmpresaFactory(usuario=admin_user, organizacao=admin_user.organizacao)
    api_client.force_authenticate(user=admin_user)
    url = reverse("empresas_api:contato-empresa-list", kwargs={"empresa_pk": empresa.pk})
    resp = api_client.get(url)
    assert resp.status_code == 200
