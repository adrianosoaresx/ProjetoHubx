import pytest
from django.urls import reverse
from django.contrib.auth import get_user_model

from accounts.models import UserType
from nucleos.models import ParticipacaoNucleo
from organizacoes.factories import OrganizacaoFactory
from nucleos.factories import NucleoFactory
from agenda.factories import EventoFactory

User = get_user_model()


@pytest.mark.django_db
def test_organizacoes_search_limited_to_user_org(client, organizacao):
    other_org = OrganizacaoFactory()
    user = User.objects.create_user(
        username="u1",
        email="u1@example.com",
        password="pass",
        user_type=UserType.NUCLEADO,
        organizacao=organizacao,
    )
    client.force_login(user)
    url = reverse("dashboard:search-organizacoes")
    resp = client.get(url, {"q": ""})
    assert resp.status_code == 200
    ids = [item["id"] for item in resp.json()["results"]]
    assert ids == [str(organizacao.id)]


@pytest.mark.django_db
def test_organizacoes_search_without_org_returns_403(client):
    user = User.objects.create_user(
        username="u2",
        email="u2@example.com",
        password="pass",
        user_type=UserType.NUCLEADO,
    )
    client.force_login(user)
    url = reverse("dashboard:search-organizacoes")
    resp = client.get(url, {"q": ""})
    assert resp.status_code == 403


@pytest.mark.django_db
def test_nucleos_search_returns_only_user_nucleos(client, organizacao):
    nucleo1 = NucleoFactory(organizacao=organizacao)
    nucleo2 = NucleoFactory(organizacao=organizacao)
    user = User.objects.create_user(
        username="u3",
        email="u3@example.com",
        password="pass",
        user_type=UserType.NUCLEADO,
        organizacao=organizacao,
    )
    ParticipacaoNucleo.objects.create(user=user, nucleo=nucleo1, status="ativo")
    client.force_login(user)
    url = reverse("dashboard:search-nucleos")
    resp = client.get(url, {"q": ""})
    assert resp.status_code == 200
    ids = [item["id"] for item in resp.json()["results"]]
    assert ids == [nucleo1.id]


@pytest.mark.django_db
def test_nucleos_search_without_participation_returns_403(client, organizacao):
    user = User.objects.create_user(
        username="u4",
        email="u4@example.com",
        password="pass",
        user_type=UserType.NUCLEADO,
        organizacao=organizacao,
    )
    client.force_login(user)
    url = reverse("dashboard:search-nucleos")
    resp = client.get(url, {"q": ""})
    assert resp.status_code == 403


@pytest.mark.django_db
def test_eventos_search_returns_only_permitted(client, organizacao):
    nucleo1 = NucleoFactory(organizacao=organizacao)
    nucleo2 = NucleoFactory(organizacao=organizacao)
    admin = User.objects.create_user(
        username="admin",
        email="admin@example.com",
        password="pass",
        user_type=UserType.ADMIN,
        organizacao=organizacao,
    )
    user = User.objects.create_user(
        username="u5",
        email="u5@example.com",
        password="pass",
        user_type=UserType.NUCLEADO,
        organizacao=organizacao,
    )
    ParticipacaoNucleo.objects.create(user=user, nucleo=nucleo1, status="ativo")
    evento1 = EventoFactory(organizacao=organizacao, nucleo=nucleo1, coordenador=admin)
    EventoFactory(organizacao=organizacao, nucleo=nucleo2, coordenador=admin)
    client.force_login(user)
    url = reverse("dashboard:search-eventos")
    resp = client.get(url, {"q": ""})
    assert resp.status_code == 200
    ids = [item["id"] for item in resp.json()["results"]]
    assert ids == [str(evento1.id)]


@pytest.mark.django_db
def test_eventos_search_without_access_returns_403(client, organizacao):
    user = User.objects.create_user(
        username="u6",
        email="u6@example.com",
        password="pass",
        user_type=UserType.NUCLEADO,
        organizacao=organizacao,
    )
    client.force_login(user)
    url = reverse("dashboard:search-eventos")
    resp = client.get(url, {"q": ""})
    assert resp.status_code == 403
