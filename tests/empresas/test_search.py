import pytest
from django.http import QueryDict

from empresas.factories import EmpresaFactory
from empresas.services import search_empresas


@pytest.mark.django_db
def test_search_considers_tags(admin_user, tag_factory):
    tag = tag_factory(nome="Tech")
    empresa = EmpresaFactory(usuario=admin_user, organizacao=admin_user.organizacao, nome="Alpha")
    empresa.tags.add(tag)
    EmpresaFactory(usuario=admin_user, organizacao=admin_user.organizacao, nome="Beta")
    qs = search_empresas(admin_user, QueryDict("q=Tech"))
    assert list(qs) == [empresa]


@pytest.mark.django_db
def test_filter_by_single_tag(admin_user, tag_factory):
    t1 = tag_factory(nome="Tech")
    t2 = tag_factory(nome="Food")
    e1 = EmpresaFactory(usuario=admin_user, organizacao=admin_user.organizacao)
    e1.tags.add(t1)
    e2 = EmpresaFactory(usuario=admin_user, organizacao=admin_user.organizacao)
    e2.tags.add(t2)
    qs = search_empresas(admin_user, QueryDict(f"tags={t1.id}"))
    assert list(qs) == [e1]


@pytest.mark.django_db
def test_filter_by_multiple_tags_and(admin_user, tag_factory):
    t1 = tag_factory(nome="Tech")
    t2 = tag_factory(nome="Food")
    e1 = EmpresaFactory(usuario=admin_user, organizacao=admin_user.organizacao)
    e1.tags.add(t1, t2)
    e2 = EmpresaFactory(usuario=admin_user, organizacao=admin_user.organizacao)
    e2.tags.add(t1)
    e3 = EmpresaFactory(usuario=admin_user, organizacao=admin_user.organizacao)
    e3.tags.add(t2)
    qs = search_empresas(admin_user, QueryDict(f"tags={t1.id}&tags={t2.id}"))
    assert set(qs) == {e1}


@pytest.mark.django_db
def test_filter_by_multiple_tags_requires_all(admin_user, tag_factory):
    t1 = tag_factory(nome="Tech")
    t2 = tag_factory(nome="Food")
    e1 = EmpresaFactory(usuario=admin_user, organizacao=admin_user.organizacao)
    e1.tags.add(t1)
    e2 = EmpresaFactory(usuario=admin_user, organizacao=admin_user.organizacao)
    e2.tags.add(t2)
    qs = search_empresas(admin_user, QueryDict(f"tags={t1.id}&tags={t2.id}"))
    assert list(qs) == []
