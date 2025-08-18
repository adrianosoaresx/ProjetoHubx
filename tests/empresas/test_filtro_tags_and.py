import time

from django.http import QueryDict

from empresas.factories import EmpresaFactory
from empresas.models import Tag
from empresas.services import search_empresas


def test_filtro_tags_and(admin_user):
    t1 = Tag.objects.create(nome="t1")
    t2 = Tag.objects.create(nome="t2")
    t3 = Tag.objects.create(nome="t3")
    e1 = EmpresaFactory(usuario=admin_user, organizacao=admin_user.organizacao, nome="Alpha")
    e1.tags.add(t1)
    e2 = EmpresaFactory(usuario=admin_user, organizacao=admin_user.organizacao, nome="Beta")
    e2.tags.add(t1, t2)
    e3 = EmpresaFactory(usuario=admin_user, organizacao=admin_user.organizacao, nome="Gamma")
    e3.tags.add(t1, t2, t3)

    params = QueryDict(mutable=True)
    params.setlist("tags", [str(t1.id), str(t2.id)])
    qs = search_empresas(admin_user, params)
    assert set(qs) == {e2, e3}

    params = QueryDict(mutable=True)
    params.setlist("tags", [str(t1.id)])
    qs = search_empresas(admin_user, params)
    assert set(qs) == {e1, e2, e3}

    params = QueryDict(mutable=True)
    params.setlist("tags", [str(t1.id), str(t2.id)])
    params["q"] = "Beta"
    qs = search_empresas(admin_user, params)
    assert list(qs) == [e2]


def test_search_performance_smoke(admin_user):
    tag = Tag.objects.create(nome="p1")
    for _ in range(5):
        emp = EmpresaFactory(usuario=admin_user, organizacao=admin_user.organizacao)
        emp.tags.add(tag)
    params = QueryDict(mutable=True)
    params.setlist("tags", [str(tag.id)])
    durations = []
    for _ in range(20):
        start = time.perf_counter()
        list(search_empresas(admin_user, params))
        durations.append(time.perf_counter() - start)
    durations.sort()
    p95 = durations[int(len(durations) * 0.95) - 1]
    assert p95 <= 0.3
