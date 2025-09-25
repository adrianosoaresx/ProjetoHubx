import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from accounts.models import UserType
from nucleos.metrics import membros_suspensos_total
from nucleos.models import Nucleo, ParticipacaoNucleo

pytestmark = pytest.mark.django_db


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def organizacao():
    from organizacoes.models import Organizacao

    return Organizacao.objects.create(nome="Org", cnpj="00.000.000/0001-00", slug="org")


@pytest.fixture
def admin_user(organizacao, django_user_model):
    return django_user_model.objects.create_user(
        username="admin",
        email="admin@example.com",
        password="pass",
        user_type=UserType.ADMIN,
        organizacao=organizacao,
    )


@pytest.fixture
def membro_user(organizacao, django_user_model):
    return django_user_model.objects.create_user(
        username="user",
        email="user@example.com",
        password="pass",
        user_type=UserType.NUCLEADO,
        organizacao=organizacao,
    )


def _auth(client, user):
    client.force_authenticate(user=user)


def test_suspender_e_reativar(api_client, admin_user, membro_user, organizacao):
    nucleo = Nucleo.objects.create(nome="N", organizacao=organizacao)
    ParticipacaoNucleo.objects.create(user=membro_user, nucleo=nucleo, status="ativo")
    _auth(api_client, admin_user)
    before = membros_suspensos_total._value.get()
    url = reverse("nucleos_api:nucleo-suspender-membro", args=[nucleo.pk, membro_user.pk])
    resp = api_client.post(url)
    assert resp.status_code == 200
    part = ParticipacaoNucleo.objects.get(user=membro_user, nucleo=nucleo)
    assert part.status_suspensao is True and part.data_suspensao is not None
    assert membros_suspensos_total._value.get() == before + 1

    url = reverse("nucleos_api:nucleo-reativar-membro", args=[nucleo.pk, membro_user.pk])
    resp = api_client.post(url)
    assert resp.status_code == 200
    part.refresh_from_db()
    assert part.status_suspensao is False and part.data_suspensao is None


def test_membro_status_endpoint(api_client, membro_user, organizacao):
    nucleo = Nucleo.objects.create(nome="N", organizacao=organizacao)
    ParticipacaoNucleo.objects.create(user=membro_user, nucleo=nucleo, status="ativo")
    _auth(api_client, membro_user)
    url = reverse("nucleos_api:nucleo-membro-status", args=[nucleo.pk])
    resp = api_client.get(url)
    assert resp.status_code == 200
    assert resp.data == {"papel": "membro", "ativo": True, "suspenso": False}

    ParticipacaoNucleo.objects.filter(user=membro_user, nucleo=nucleo).update(status_suspensao=True)
    resp = api_client.get(url)
    assert resp.data == {"papel": "membro", "ativo": True, "suspenso": True}
