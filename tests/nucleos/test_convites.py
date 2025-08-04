import pytest
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from accounts.models import UserType
from nucleos.models import ConviteNucleo, Nucleo, ParticipacaoNucleo

pytestmark = pytest.mark.django_db


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def organizacao():
    from organizacoes.models import Organizacao

    return Organizacao.objects.create(nome="Org", cnpj="00.000.000/0001-00")


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


def test_convite_flow(api_client, admin_user, membro_user, organizacao):
    nucleo = Nucleo.objects.create(nome="N", slug="n", organizacao=organizacao)
    _auth(api_client, admin_user)
    url = reverse("nucleos_api:nucleo-convite")
    resp = api_client.post(
        url, {"email": membro_user.email, "papel": "membro", "nucleo": nucleo.pk}
    )
    assert resp.status_code == 201
    token = resp.data["token"]

    _auth(api_client, membro_user)
    accept_url = reverse("nucleos_api:nucleo-aceitar-convite") + f"?token={token}"
    resp = api_client.get(accept_url)
    assert resp.status_code == 200
    assert ParticipacaoNucleo.objects.filter(
        user=membro_user, nucleo=nucleo, status="aprovado"
    ).exists()


def test_convite_apenas_admin(api_client, membro_user, organizacao):
    nucleo = Nucleo.objects.create(nome="N2", slug="n2", organizacao=organizacao)
    _auth(api_client, membro_user)
    url = reverse("nucleos_api:nucleo-convite")
    resp = api_client.post(
        url, {"email": "alguem@example.com", "papel": "membro", "nucleo": nucleo.pk}
    )
    assert resp.status_code == 403


def test_convite_expirado(api_client, admin_user, membro_user, organizacao):
    nucleo = Nucleo.objects.create(nome="N3", slug="n3", organizacao=organizacao)
    convite = ConviteNucleo.objects.create(
        email=membro_user.email, papel="membro", nucleo=nucleo
    )
    ConviteNucleo.objects.filter(pk=convite.pk).update(
        criado_em=timezone.now() - timezone.timedelta(days=8)
    )
    _auth(api_client, membro_user)
    url = reverse("nucleos_api:nucleo-aceitar-convite") + f"?token={convite.token}"
    resp = api_client.get(url)
    assert resp.status_code == 400

