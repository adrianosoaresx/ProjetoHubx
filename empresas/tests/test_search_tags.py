import pytest
from django.http import QueryDict
from django.urls import reverse
from rest_framework.test import APIClient

from accounts.factories import UserFactory
from accounts.models import UserType
from empresas.factories import EmpresaFactory
from empresas.models import Tag
from empresas.services import search_empresas


@pytest.mark.django_db
def test_search_empresas_tags_and():
    tag1 = Tag.objects.create(nome="t1")
    tag2 = Tag.objects.create(nome="t2")
    tag3 = Tag.objects.create(nome="t3")
    empresa1 = EmpresaFactory()
    empresa1.tags.add(tag1, tag2, tag3)
    empresa2 = EmpresaFactory()
    empresa2.tags.add(tag1, tag2)
    user = UserFactory(is_superuser=True, user_type=UserType.ROOT)
    params = QueryDict(mutable=True)
    params.setlist("tags", [str(tag1.id), str(tag2.id), str(tag3.id)])
    qs = search_empresas(user, params)
    assert list(qs) == [empresa1]


@pytest.mark.django_db
def test_api_filter_tags_and():
    tag1 = Tag.objects.create(nome="t1")
    tag2 = Tag.objects.create(nome="t2")
    tag3 = Tag.objects.create(nome="t3")
    empresa1 = EmpresaFactory()
    empresa1.tags.add(tag1, tag2, tag3)
    empresa2 = EmpresaFactory()
    empresa2.tags.add(tag1, tag2)
    user = UserFactory(is_superuser=True, user_type=UserType.ROOT)
    client = APIClient()
    client.force_authenticate(user)
    url = reverse("empresas_api:empresa-list")
    resp = client.get(url, {"tags": [tag1.id, tag2.id, tag3.id]})
    ids = {item["id"] for item in resp.json()}
    assert ids == {str(empresa1.id)}
