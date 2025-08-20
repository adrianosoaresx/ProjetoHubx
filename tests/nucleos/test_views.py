import csv
from datetime import timedelta

import pytest
from django.contrib.auth import get_user_model
from django.http import HttpResponseBadRequest
from django.test import RequestFactory
from django.urls import reverse
from django.utils import timezone

from accounts.models import UserType
from nucleos.models import CoordenadorSuplente, Nucleo, ParticipacaoNucleo
from nucleos.views import SuplenteCreateView
from nucleos.forms import SuplenteForm
from organizacoes.models import Organizacao

pytestmark = pytest.mark.django_db


@pytest.fixture
def organizacao():
    return Organizacao.objects.create(nome="Org", cnpj="00.000.000/0001-00", slug="org")


@pytest.fixture
def admin_user(organizacao):
    User = get_user_model()
    return User.objects.create_user(
        username="admin",
        email="admin@example.com",
        password="pass",
        user_type=UserType.ADMIN,
        organizacao=organizacao,
    )


@pytest.fixture
def membro_user(organizacao):
    User = get_user_model()
    return User.objects.create_user(
        username="membro",
        email="membro@example.com",
        password="pass",
        user_type=UserType.NUCLEADO,
        organizacao=organizacao,
    )


@pytest.fixture(autouse=True)
def patch_tasks(monkeypatch):
    class Dummy:
        def delay(self, *args, **kwargs):
            return None

    monkeypatch.setattr("nucleos.views.notify_participacao_aprovada", Dummy())
    monkeypatch.setattr("nucleos.views.notify_participacao_recusada", Dummy())
    monkeypatch.setattr("nucleos.views.notify_exportacao_membros", Dummy())
    monkeypatch.setattr("nucleos.views.notify_suplente_designado", Dummy())


def test_nucleo_create_and_soft_delete(client, admin_user, organizacao):
    client.force_login(admin_user)
    resp = client.post(
        reverse("nucleos:create"),
        data={"nome": "N1", "slug": "n1", "descricao": "d", "ativo": True},
    )
    assert resp.status_code == 302
    nucleo = Nucleo.objects.get(nome="N1")
    assert not nucleo.deleted
    resp = client.post(reverse("nucleos:delete", args=[nucleo.pk]))
    nucleo.refresh_from_db()
    assert nucleo.deleted is True


def test_participacao_flow(client, admin_user, membro_user, organizacao):
    nucleo = Nucleo.objects.create(nome="N", slug="n", organizacao=organizacao)
    client.force_login(membro_user)
    client.post(reverse("nucleos:participacao_solicitar", args=[nucleo.pk]))
    part = ParticipacaoNucleo.objects.get(user=membro_user, nucleo=nucleo)
    assert part.status == "pendente"
    client.force_login(admin_user)
    client.post(
        reverse("nucleos:participacao_decidir", args=[nucleo.pk, part.pk]),
        data={"acao": "approve"},
    )
    part.refresh_from_db()
    assert part.status == "ativo"
    assert list(nucleo.membros) == [membro_user]


def test_exportar_membros_csv(client, admin_user, organizacao):
    nucleo = Nucleo.objects.create(nome="N", slug="n", organizacao=organizacao)
    ParticipacaoNucleo.objects.create(
        user=admin_user, nucleo=nucleo, status="ativo", papel="coordenador"
    )
    client.force_login(admin_user)
    resp = client.get(reverse("nucleos:exportar_membros", args=[nucleo.pk]))
    assert resp.status_code == 200
    reader = csv.reader(resp.content.decode().splitlines())
    rows = list(reader)
    assert rows[0] == [
        "Nome",
        "Email",
        "Status",
        "papel",
        "is_suplente",
        "data_ingresso",
    ]


def test_toggle_active(client, admin_user, organizacao):
    nucleo = Nucleo.objects.create(nome="N", slug="n", organizacao=organizacao)
    client.force_login(admin_user)
    resp = client.post(reverse("nucleos:toggle_active", args=[nucleo.pk]))
    assert resp.status_code == 302
    nucleo.refresh_from_db()
    assert nucleo.deleted is True


def test_suplente_create_non_member(admin_user, organizacao, monkeypatch):
    nucleo = Nucleo.objects.create(nome="N", slug="n", organizacao=organizacao)
    User = get_user_model()
    nao_membro = User.objects.create_user(
        username="x",
        email="x@example.com",
        password="pass",
        user_type=UserType.NUCLEADO,
        organizacao=organizacao,
    )

    request = RequestFactory().post(
        "/", {
            "usuario": nao_membro.id,
            "periodo_inicio": timezone.now().strftime("%Y-%m-%d"),
            "periodo_fim": (timezone.now() + timedelta(days=1)).strftime("%Y-%m-%d"),
        }
    )
    request.user = admin_user

    view = SuplenteCreateView()
    view.request = request
    view.kwargs = {"pk": nucleo.pk}

    def _form_invalid(self, form):
        return HttpResponseBadRequest()

    monkeypatch.setattr(SuplenteCreateView, "form_invalid", _form_invalid)

    form = SuplenteForm(data=request.POST, nucleo=nucleo)
    form.fields["usuario"].queryset = User.objects.all()
    assert form.is_valid()
    response = view.form_valid(form)
    assert response.status_code == 400
    assert "Usuário não é membro do núcleo." in form.errors["usuario"]
    assert CoordenadorSuplente.objects.count() == 0


def test_suplente_create_overlap(admin_user, membro_user, organizacao, monkeypatch):
    nucleo = Nucleo.objects.create(nome="N", slug="n", organizacao=organizacao)
    ParticipacaoNucleo.objects.create(
        nucleo=nucleo, user=membro_user, status="ativo"
    )
    now = timezone.now()
    CoordenadorSuplente.objects.create(
        nucleo=nucleo,
        usuario=membro_user,
        periodo_inicio=now,
        periodo_fim=now + timedelta(days=5),
    )

    request = RequestFactory().post(
        "/", {
            "usuario": membro_user.id,
            "periodo_inicio": (now + timedelta(days=1)).strftime("%Y-%m-%d"),
            "periodo_fim": (now + timedelta(days=2)).strftime("%Y-%m-%d"),
        }
    )
    request.user = admin_user

    view = SuplenteCreateView()
    view.request = request
    view.kwargs = {"pk": nucleo.pk}

    def _form_invalid(self, form):
        return HttpResponseBadRequest()

    monkeypatch.setattr(SuplenteCreateView, "form_invalid", _form_invalid)

    form = SuplenteForm(data=request.POST, nucleo=nucleo)
    assert form.is_valid()
    response = view.form_valid(form)
    assert response.status_code == 400
    assert "Usuário já é suplente no período informado." in form.non_field_errors()
    assert CoordenadorSuplente.objects.count() == 1


def test_suplente_create_success(client, admin_user, membro_user, organizacao):
    nucleo = Nucleo.objects.create(nome="N", slug="n", organizacao=organizacao)
    ParticipacaoNucleo.objects.create(
        nucleo=nucleo, user=membro_user, status="ativo"
    )
    client.force_login(admin_user)
    inicio = timezone.now()
    fim = inicio + timedelta(days=2)
    resp = client.post(
        reverse("nucleos:suplente_adicionar", args=[nucleo.pk]),
        data={
            "usuario": membro_user.id,
            "periodo_inicio": inicio.strftime("%Y-%m-%d"),
            "periodo_fim": fim.strftime("%Y-%m-%d"),
        },
    )
    assert resp.status_code == 302
    assert CoordenadorSuplente.objects.filter(
        nucleo=nucleo, usuario=membro_user
    ).exists()
