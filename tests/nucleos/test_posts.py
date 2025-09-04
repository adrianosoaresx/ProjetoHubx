import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from accounts.models import UserType
from feed.models import Post
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
def membro_user(organizacao, django_user_model):
    return django_user_model.objects.create_user(
        username="user",
        email="user@example.com",
        password="pass",
        user_type=UserType.NUCLEADO,
        organizacao=organizacao,
    )


@pytest.fixture
def outro_user(organizacao, django_user_model):
    return django_user_model.objects.create_user(
        username="other",
        email="other@example.com",
        password="pass",
        user_type=UserType.NUCLEADO,
        organizacao=organizacao,
    )


def _auth(client, user):
    client.force_authenticate(user=user)


def test_postar_no_feed(api_client, membro_user, organizacao):
    nucleo = Nucleo.objects.create(nome="N", organizacao=organizacao)
    ParticipacaoNucleo.objects.create(user=membro_user, nucleo=nucleo, status="ativo")
    _auth(api_client, membro_user)
    url = reverse("nucleos_api:nucleo-posts", kwargs={"pk": nucleo.pk})
    resp = api_client.post(url, {"conteudo": "olá"})
    assert resp.status_code == 201
    assert Post.objects.filter(nucleo=nucleo, autor=membro_user).exists()


def test_postar_requer_membro(api_client, outro_user, organizacao):
    nucleo = Nucleo.objects.create(nome="N2", organizacao=organizacao)
    _auth(api_client, outro_user)
    url = reverse("nucleos_api:nucleo-posts", kwargs={"pk": nucleo.pk})
    resp = api_client.post(url, {"conteudo": "oi"})
    assert resp.status_code == 403
    assert Post.objects.count() == 0
