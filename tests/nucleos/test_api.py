import csv
from datetime import timedelta
import csv

import pytest
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from accounts.models import UserType
from nucleos.models import CoordenadorSuplente, Nucleo, ParticipacaoNucleo
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


def test_solicitar_aprovar_recusar(api_client, admin_user, outro_user, organizacao, django_user_model):
    nucleo = Nucleo.objects.create(nome="N1", slug="n1", organizacao=organizacao)

    _auth(api_client, outro_user)
    url = reverse("nucleos_api:nucleo-solicitar", args=[nucleo.pk])
    resp = api_client.post(url)
    assert resp.status_code == 201

    _auth(api_client, admin_user)
    url_aprovar = reverse(
        "nucleos_api:nucleo-aprovar-membro", args=[nucleo.pk, outro_user.pk]
    )
    resp = api_client.post(url_aprovar)
    assert resp.status_code == 200
    p = ParticipacaoNucleo.objects.get(nucleo=nucleo, user=outro_user)
    assert p.status == "ativo" and p.decidido_por == admin_user

    novo = django_user_model.objects.create_user(
        username="novo", email="novo@example.com", password="pass", user_type=UserType.NUCLEADO, organizacao=organizacao
    )
    _auth(api_client, novo)
    resp = api_client.post(url)
    assert resp.status_code == 201
    _auth(api_client, admin_user)
    url_recusar = reverse(
        "nucleos_api:nucleo-recusar-membro", args=[nucleo.pk, novo.pk]
    )
    resp = api_client.post(url_recusar, {"justificativa": "motivo"})
    assert resp.status_code == 200
    p2 = ParticipacaoNucleo.objects.get(nucleo=nucleo, user=novo)
    assert p2.status == "inativo" and p2.justificativa == "motivo"


def test_expiracao_automatica(api_client, outro_user, organizacao):
    nucleo = Nucleo.objects.create(nome="N2", slug="n2", organizacao=organizacao)
    part = ParticipacaoNucleo.objects.create(user=outro_user, nucleo=nucleo)
    ParticipacaoNucleo.objects.filter(pk=part.pk).update(data_solicitacao=timezone.now() - timedelta(days=31))
    expirar_solicitacoes_pendentes()
    part.refresh_from_db()
    assert part.status == "inativo" and part.justificativa == "expiração automática"


def test_suplente_crud(api_client, admin_user, coord_user, organizacao):
    nucleo = Nucleo.objects.create(nome="N3", slug="n3", organizacao=organizacao)
    ParticipacaoNucleo.objects.create(
        user=coord_user, nucleo=nucleo, status="ativo"
    )
    _auth(api_client, admin_user)
    url = reverse("nucleos_api:nucleo-suplentes", args=[nucleo.pk])
    data = {
        "usuario": coord_user.pk,
        "periodo_inicio": timezone.now(),
        "periodo_fim": timezone.now() + timedelta(days=1),
    }
    resp = api_client.post(url, data)
    assert resp.status_code == 201
    suplente_id = resp.data["id"]
    resp = api_client.get(url)
    assert resp.status_code == 200 and resp.data[0]["status"] == "ativo"
    url_del = reverse("nucleos_api:nucleo-remover-suplente", args=[nucleo.pk, suplente_id])
    resp = api_client.delete(url_del)
    assert resp.status_code == 204
    assert not CoordenadorSuplente.objects.filter(id=suplente_id).exists()


def test_suplente_validations(api_client, admin_user, coord_user, outro_user, organizacao):
    nucleo = Nucleo.objects.create(nome="N5", slug="n5", organizacao=organizacao)
    ParticipacaoNucleo.objects.create(
        user=coord_user, nucleo=nucleo, status="ativo"
    )
    _auth(api_client, admin_user)
    url = reverse("nucleos_api:nucleo-suplentes", args=[nucleo.pk])
    now = timezone.now()
    data = {
        "usuario": coord_user.pk,
        "periodo_inicio": now,
        "periodo_fim": now + timedelta(days=2),
    }
    assert api_client.post(url, data).status_code == 201
    # Overlap
    assert api_client.post(url, data).status_code == 400
    # Not member
    data["usuario"] = outro_user.pk
    resp = api_client.post(url, data)
    assert resp.status_code == 400


def test_exportar_membros(api_client, admin_user, outro_user, organizacao):
    nucleo = Nucleo.objects.create(nome="N4", slug="n4", organizacao=organizacao)
    ParticipacaoNucleo.objects.create(user=outro_user, nucleo=nucleo, status="ativo")
    _auth(api_client, admin_user)
    # designa suplente
    url_supl = reverse("nucleos_api:nucleo-suplentes", args=[nucleo.pk])
    api_client.post(
        url_supl,
        {
            "usuario": outro_user.pk,
            "periodo_inicio": timezone.now(),
            "periodo_fim": timezone.now() + timedelta(days=1),
        },
    )
    url = reverse("nucleos_api:nucleo-exportar-membros", args=[nucleo.pk])
    resp = api_client.get(url + "?formato=csv")
    assert resp.status_code == 200
    rows = list(csv.reader(resp.content.decode().splitlines()))
    assert rows[0] == [
        "Nome",
        "Email",
        "Status",
        "papel",
        "is_suplente",
        "data_ingresso",
    ]
    assert "True" in rows[1] or "False" in rows[1]
    resp = api_client.get(url + "?formato=xls")
    assert resp.status_code == 200
    assert (
        resp["Content-Type"]
        == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )


def test_permission_denied(api_client, outro_user, organizacao):
    nucleo = Nucleo.objects.create(nome="N6", slug="n6", organizacao=organizacao)
    _auth(api_client, outro_user)
    url = reverse("nucleos_api:nucleo-suplentes", args=[nucleo.pk])
    resp = api_client.post(
        url,
        {
            "usuario": outro_user.pk,
            "periodo_inicio": timezone.now(),
            "periodo_fim": timezone.now() + timedelta(days=1),
        },
    )
    assert resp.status_code == 403
    export_url = reverse("nucleos_api:nucleo-exportar-membros", args=[nucleo.pk])
    assert api_client.get(export_url).status_code == 403


def test_inter_org_forbidden(api_client, admin_user, organizacao, django_user_model):
    outra = Organizacao.objects.create(nome="OrgX", cnpj="11.111.111/0001-11", slug="orgx")
    outsider = django_user_model.objects.create_user(
        username="outsider",
        email="o@example.com",
        password="pass",
        user_type=UserType.ADMIN,
        organizacao=outra,
    )
    nucleo = Nucleo.objects.create(nome="N8", slug="n8", organizacao=organizacao)
    _auth(api_client, outsider)
    url = reverse("nucleos_api:nucleo-aprovar-membro", args=[nucleo.pk, admin_user.pk])
    assert api_client.post(url).status_code == 403


def test_membros_ativos_endpoint(api_client, admin_user, outro_user, organizacao):
    nucleo = Nucleo.objects.create(nome="N9", slug="n9", organizacao=organizacao)
    ParticipacaoNucleo.objects.create(user=admin_user, nucleo=nucleo, status="ativo", papel="coordenador")
    ParticipacaoNucleo.objects.create(
        user=outro_user, nucleo=nucleo, status="ativo", status_suspensao=True
    )
    _auth(api_client, admin_user)
    url = reverse("nucleos_api:nucleo-membros-ativos", args=[nucleo.pk])
    resp = api_client.get(url)
    assert resp.status_code == 200
    assert len(resp.data["results"]) == 1
    assert resp.data["results"][0]["papel"] == "coordenador"


def test_financeiro_signal(api_client, admin_user, outro_user, organizacao, monkeypatch):
    nucleo = Nucleo.objects.create(nome="N10", slug="n10", organizacao=organizacao)
    ParticipacaoNucleo.objects.create(user=outro_user, nucleo=nucleo)
    calls: list[tuple] = []
    monkeypatch.setattr("nucleos.signals.atualizar_cobranca", lambda *args: calls.append(args))
    _auth(api_client, admin_user)
    url = reverse("nucleos_api:nucleo-aprovar-membro", args=[nucleo.pk, outro_user.pk])
    api_client.post(url)
    assert calls and calls[0][2] == "ativo"

def test_metrics_endpoint_cache(api_client, admin_user, organizacao, outro_user):
    nucleo = Nucleo.objects.create(nome="N7", slug="n7", organizacao=organizacao)
    ParticipacaoNucleo.objects.create(user=admin_user, nucleo=nucleo, status="ativo")
    ParticipacaoNucleo.objects.create(
        user=outro_user, nucleo=nucleo, status="ativo", status_suspensao=True
    )
    _auth(api_client, admin_user)
    url = reverse("nucleos_api:nucleo-metrics", args=[nucleo.pk])
    resp = api_client.get(url)
    assert resp.status_code == 200
    assert resp["X-Cache"] == "MISS"
    assert resp.data["total_membros"] == 1
    resp2 = api_client.get(url)
    assert resp2["X-Cache"] == "HIT"
