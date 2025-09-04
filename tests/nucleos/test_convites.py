import pytest
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from accounts.models import UserType
from nucleos.metrics import convites_gerados_total, convites_usados_total
from nucleos.models import ConviteNucleo, Nucleo, ParticipacaoNucleo
from services.nucleos import user_belongs_to_nucleo

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


def test_convite_flow(api_client, admin_user, membro_user, organizacao):
    nucleo = Nucleo.objects.create(nome="N", organizacao=organizacao)
    before_generated = convites_gerados_total._value.get()
    before_used = convites_usados_total._value.get()

    _auth(api_client, admin_user)
    url = reverse("nucleos_api:nucleo-convites", kwargs={"pk": nucleo.pk})
    resp = api_client.post(url, {"email": membro_user.email, "papel": "membro"})
    assert resp.status_code == 201
    token = resp.data["token"]
    assert convites_gerados_total._value.get() == before_generated + 1

    _auth(api_client, membro_user)
    accept_url = reverse("nucleos_api:nucleo-aceitar-convite") + f"?token={token}"
    resp = api_client.get(accept_url)
    assert resp.status_code == 200
    assert ParticipacaoNucleo.objects.filter(user=membro_user, nucleo=nucleo, status="ativo").exists()
    assert convites_usados_total._value.get() == before_used + 1


def test_convite_apenas_admin(api_client, membro_user, organizacao):
    nucleo = Nucleo.objects.create(nome="N2", organizacao=organizacao)
    _auth(api_client, membro_user)
    url = reverse("nucleos_api:nucleo-convites", kwargs={"pk": nucleo.pk})
    resp = api_client.post(url, {"email": "alguem@example.com", "papel": "membro"})
    assert resp.status_code == 403


def test_convite_expirado(api_client, admin_user, membro_user, organizacao):
    nucleo = Nucleo.objects.create(nome="N3", organizacao=organizacao)
    convite = ConviteNucleo.objects.create(email=membro_user.email, papel="membro", nucleo=nucleo)
    ConviteNucleo.objects.filter(pk=convite.pk).update(created_at=timezone.now() - timezone.timedelta(days=8))
    _auth(api_client, membro_user)
    url = reverse("nucleos_api:nucleo-aceitar-convite") + f"?token={convite.token}"
    resp = api_client.get(url)
    assert resp.status_code == 400


def test_user_belongs_to_nucleo_suspenso(membro_user, organizacao):
    nucleo = Nucleo.objects.create(nome="N4", organizacao=organizacao)
    ParticipacaoNucleo.objects.create(
        user=membro_user,
        nucleo=nucleo,
        status="ativo",
        status_suspensao=True,
    )
    participa, info, suspenso = user_belongs_to_nucleo(membro_user, nucleo.id)
    assert participa is True
    assert info == "membro:ativo"
    assert suspenso is True


def test_revogar_convite(api_client, admin_user, membro_user, organizacao):
    nucleo = Nucleo.objects.create(nome="N5", organizacao=organizacao)
    _auth(api_client, admin_user)
    create_url = reverse("nucleos_api:nucleo-convites", kwargs={"pk": nucleo.pk})
    resp = api_client.post(create_url, {"email": membro_user.email, "papel": "membro"})
    convite_id = resp.data["id"]
    delete_url = reverse(
        "nucleos_api:nucleo-revogar-convite",
        kwargs={"pk": nucleo.pk, "convite_id": convite_id},
    )
    resp = api_client.delete(delete_url)
    assert resp.status_code == 204
    convite = ConviteNucleo.objects.get(pk=convite_id)
    assert convite.usado_em is not None


def test_convite_quota_diaria(api_client, admin_user, organizacao):
    from django.core.cache import cache
    from django.test import override_settings

    nucleo = Nucleo.objects.create(nome="N6", organizacao=organizacao)
    _auth(api_client, admin_user)
    url = reverse("nucleos_api:nucleo-convites", kwargs={"pk": nucleo.pk})
    cache.clear()
    with override_settings(CONVITE_NUCLEO_DIARIO_LIMITE=1):
        resp1 = api_client.post(url, {"email": "a@example.com", "papel": "membro"})
        assert resp1.status_code == 201
        resp2 = api_client.post(url, {"email": "b@example.com", "papel": "membro"})
        assert resp2.status_code == 429


def test_convite_nao_pode_ser_reutilizado(api_client, membro_user, organizacao):
    nucleo = Nucleo.objects.create(nome="N7", organizacao=organizacao)
    convite = ConviteNucleo.objects.create(email=membro_user.email, papel="membro", nucleo=nucleo)
    _auth(api_client, membro_user)
    url = reverse("nucleos_api:nucleo-aceitar-convite") + f"?token={convite.token}"
    resp1 = api_client.get(url)
    assert resp1.status_code == 200
    resp2 = api_client.get(url)
    assert resp2.status_code == 400
    assert resp2.data["detail"] == "Convite já utilizado."
