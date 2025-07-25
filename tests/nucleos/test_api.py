import csv
from datetime import timedelta

import pytest
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from accounts.models import UserType
from nucleos.models import Nucleo, ParticipacaoNucleo, CoordenadorSuplente
from nucleos.tasks import expirar_solicitacoes_pendentes
from organizacoes.models import Organizacao

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def celery_eager(settings, monkeypatch):
    settings.CELERY_TASK_ALWAYS_EAGER = True
    monkeypatch.setattr("nucleos.tasks.notify_participacao_aprovada.delay", lambda *a, **k: None)
    monkeypatch.setattr("nucleos.tasks.notify_participacao_recusada.delay", lambda *a, **k: None)
    monkeypatch.setattr("nucleos.tasks.notify_suplente_designado.delay", lambda *a, **k: None)
    monkeypatch.setattr("nucleos.tasks.notify_exportacao_membros.delay", lambda *a, **k: None)


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def organizacao():
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
def coord_user(organizacao, django_user_model):
    return django_user_model.objects.create_user(
        username="coord",
        email="coord@example.com",
        password="pass",
        user_type=UserType.COORDENADOR,
        organizacao=organizacao,
    )


@pytest.fixture
def outro_user(organizacao, django_user_model):
    return django_user_model.objects.create_user(
        username="outro",
        email="outro@example.com",
        password="pass",
        user_type=UserType.NUCLEADO,
        organizacao=organizacao,
    )


def _auth(client, user):
    client.force_authenticate(user=user)


def test_solicitar_aprovar_recusar(api_client, admin_user, outro_user, organizacao):
    nucleo = Nucleo.objects.create(nome="N1", organizacao=organizacao)
    _auth(api_client, outro_user)
    url = reverse("nucleos_api:nucleo-participacoes", args=[nucleo.pk])
    resp = api_client.post(url)
    assert resp.status_code == 201
    participacao_id = resp.data["id"]

    _auth(api_client, admin_user)
    url_decidir = reverse(
        "nucleos_api:nucleo-decidir-participacao",
        args=[nucleo.pk, participacao_id],
    )
    resp = api_client.patch(url_decidir, {"acao": "approve"})
    assert resp.status_code == 200
    p = ParticipacaoNucleo.objects.get(pk=participacao_id)
    assert p.status == "aprovado" and p.decidido_por == admin_user

    # second request to reject should fail
    resp = api_client.patch(url_decidir, {"acao": "reject"})
    assert resp.status_code == 400


def test_expiracao_automatica(api_client, outro_user, organizacao):
    nucleo = Nucleo.objects.create(nome="N2", organizacao=organizacao)
    part = ParticipacaoNucleo.objects.create(user=outro_user, nucleo=nucleo)
    ParticipacaoNucleo.objects.filter(pk=part.pk).update(data_solicitacao=timezone.now() - timedelta(days=31))
    expirar_solicitacoes_pendentes()
    part.refresh_from_db()
    assert part.status == "recusado"


def test_designar_suplente(api_client, admin_user, coord_user, organizacao):
    nucleo = Nucleo.objects.create(nome="N3", organizacao=organizacao)
    _auth(api_client, admin_user)
    url = reverse("nucleos_api:nucleo-adicionar-suplente", args=[nucleo.pk])
    data = {
        "usuario": coord_user.pk,
        "periodo_inicio": timezone.now(),
        "periodo_fim": timezone.now() + timedelta(days=1),
    }
    resp = api_client.post(url, data)
    assert resp.status_code == 201
    assert CoordenadorSuplente.objects.filter(nucleo=nucleo, usuario=coord_user).exists()


def test_exportar_membros(api_client, admin_user, outro_user, organizacao):
    nucleo = Nucleo.objects.create(nome="N4", organizacao=organizacao)
    ParticipacaoNucleo.objects.create(user=outro_user, nucleo=nucleo, status="aprovado")
    _auth(api_client, admin_user)
    url = reverse("nucleos_api:nucleo-exportar-membros", args=[nucleo.pk])
    resp = api_client.get(url)
    assert resp.status_code == 200
    rows = list(csv.reader(resp.content.decode().splitlines()))
    assert rows[0] == ["Nome", "Email", "Status", "Função"]
    assert outro_user.email in rows[1]
