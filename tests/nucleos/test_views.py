import pytest
from django.contrib.auth import get_user_model
from django.test import RequestFactory
from django.urls import reverse
from django.utils import timezone

from accounts.models import UserType
from nucleos.models import CoordenadorSuplente, Nucleo, ParticipacaoNucleo
from nucleos.views import NucleoDetailView
from organizacoes.models import Organizacao
from eventos.factories import EventoFactory

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


def test_nucleo_create_and_soft_delete(client, admin_user, organizacao):
    client.force_login(admin_user)
    resp = client.post(
        reverse("nucleos:create"),
        data={
            "nome": "N1",
            "descricao": "d",
            "classificacao": Nucleo.Classificacao.PLANEJAMENTO,
            "ativo": True,
            "mensalidade": "30.00",
        },
    )
    assert resp.status_code == 302
    nucleo = Nucleo.objects.get(nome="N1")
    assert not nucleo.deleted
    resp = client.get(reverse("nucleos:delete", args=[nucleo.pk]))
    assert resp.status_code == 200
    resp = client.post(reverse("nucleos:delete", args=[nucleo.pk]))
    nucleo.refresh_from_db()
    assert nucleo.deleted is True


def test_participacao_flow(client, admin_user, membro_user, organizacao):
    nucleo = Nucleo.objects.create(nome="N", organizacao=organizacao)
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


def test_participacao_reuse_soft_deleted(client, membro_user, organizacao):
    nucleo = Nucleo.objects.create(nome="N", organizacao=organizacao)
    part = ParticipacaoNucleo.objects.create(user=membro_user, nucleo=nucleo, status="ativo")
    part.soft_delete()

    client.force_login(membro_user)
    resp = client.post(reverse("nucleos:participacao_solicitar", args=[nucleo.pk]))
    assert resp.status_code == 302

    part.refresh_from_db()
    assert part.status == "pendente"
    assert part.deleted is False and part.deleted_at is None
    assert ParticipacaoNucleo.all_objects.filter(user=membro_user, nucleo=nucleo).count() == 1


def test_toggle_active(client, admin_user, organizacao):
    nucleo = Nucleo.objects.create(nome="N", organizacao=organizacao)
    client.force_login(admin_user)
    resp = client.post(reverse("nucleos:toggle_active", args=[nucleo.pk]))
    assert resp.status_code == 302
    nucleo.refresh_from_db()
    assert nucleo.deleted is True


def test_toggle_active_admin_other_org(client, organizacao, admin_user):
    other_org = Organizacao.objects.create(nome="Org2", cnpj="11.111.111/1111-11", slug="org2")
    nucleo = Nucleo.objects.create(nome="N", organizacao=organizacao)
    User = get_user_model()
    other_admin = User.objects.create_user(
        username="admin2",
        email="admin2@example.com",
        password="pass",
        user_type=UserType.ADMIN,
        organizacao=other_org,
    )
    client.force_login(other_admin)
    resp = client.post(reverse("nucleos:toggle_active", args=[nucleo.pk]))
    assert resp.status_code == 302
    nucleo.refresh_from_db()
    assert nucleo.deleted is False


def test_meus_nucleos_view(client, membro_user, organizacao):
    nucleo1 = Nucleo.objects.create(nome="N1", organizacao=organizacao)
    nucleo2 = Nucleo.objects.create(nome="N2", organizacao=organizacao)
    ParticipacaoNucleo.objects.create(nucleo=nucleo1, user=membro_user, status="ativo")
    ParticipacaoNucleo.objects.create(nucleo=nucleo2, user=membro_user, status="inativo")
    client.force_login(membro_user)
    resp = client.get(reverse("nucleos:meus"))
    assert resp.status_code == 200
    assert list(resp.context["object_list"]) == [nucleo1]


def test_meus_nucleos_view_admin_redirect(client, admin_user):
    client.force_login(admin_user)
    resp = client.get(reverse("nucleos:meus"))
    assert resp.status_code in (302, 403)
    if resp.status_code == 302:
        assert resp.url == reverse("nucleos:list")


def test_nucleo_detail_view_queries(admin_user, organizacao, django_assert_num_queries):
    User = get_user_model()
    nucleo = Nucleo.objects.create(nome="NQ", organizacao=organizacao)
    members = []
    for i in range(3):
        u = User.objects.create_user(
            username=f"m{i}",
            email=f"m{i}@example.com",
            password="pass",
            user_type=UserType.NUCLEADO,
            organizacao=organizacao,
        )
        ParticipacaoNucleo.objects.create(
            nucleo=nucleo,
            user=u,
            status="ativo",
            papel="coordenador" if i == 0 else "membro",
            papel_coordenador=(
                ParticipacaoNucleo.PapelCoordenador.COORDENADOR_GERAL if i == 0 else None
            ),
        )
        members.append(u)
    pend = User.objects.create_user(
        username="pendente",
        email="pendente@example.com",
        password="pass",
        user_type=UserType.NUCLEADO,
        organizacao=organizacao,
    )
    ParticipacaoNucleo.objects.create(nucleo=nucleo, user=pend, status="pendente")
    CoordenadorSuplente.objects.create(
        nucleo=nucleo,
        usuario=members[0],
        periodo_inicio=timezone.now(),
        periodo_fim=timezone.now(),
    )
    EventoFactory.create(organizacao=organizacao, nucleo=nucleo, coordenador=admin_user)
    request = RequestFactory().get("/")
    request.user = admin_user
    view = NucleoDetailView()
    view.request = request
    view.kwargs = {"pk": nucleo.pk}
    with django_assert_num_queries(16):
        qs = view.get_queryset()
        obj = qs.get()
        view.object = obj
        ctx = view.get_context_data()
        page_obj = ctx["page_obj"]
        assert page_obj.paginator.count == len(members)
        for p in page_obj.object_list:
            _ = p.user
        for p in ctx["membros_ativos"]:
            _ = p.user
        for p in ctx["coordenadores"]:
            _ = p.user
        for p in ctx["membros_pendentes"]:
            _ = p.user
        suplentes = ctx["suplentes"]
        bool(suplentes)
        list(suplentes)
        eventos = list(ctx["eventos"])
        assert eventos[0].num_inscritos == 0


def test_nucleo_list_filtra_para_associado(client, organizacao):
    other_org = Organizacao.objects.create(nome="Org2", cnpj="11.111.111/0001-11", slug="org2")
    Nucleo.objects.create(nome="N1", organizacao=organizacao)
    Nucleo.objects.create(nome="N2", organizacao=other_org)
    User = get_user_model()
    assoc = User.objects.create_user(
        username="assoc",
        email="assoc@example.com",
        password="pwd",
        user_type=UserType.ASSOCIADO,
        organizacao=organizacao,
    )
    client.force_login(assoc)
    resp = client.get(reverse("nucleos:list"))
    assert resp.status_code == 200
    nomes = [n.nome for n in resp.context["object_list"]]
    assert "N1" in nomes
    assert "N2" not in nomes


def test_nucleo_list_filtra_para_nucleado(client, organizacao):
    other_org = Organizacao.objects.create(nome="Org2", cnpj="22.222.222/0002-22", slug="org22")
    Nucleo.objects.create(nome="N1", organizacao=organizacao)
    Nucleo.objects.create(nome="N2", organizacao=other_org)
    User = get_user_model()
    nucleado = User.objects.create_user(
        username="nuc",
        email="nuc@example.com",
        password="pwd",
        user_type=UserType.NUCLEADO,
        organizacao=organizacao,
    )
    client.force_login(nucleado)
    resp = client.get(reverse("nucleos:list"))
    assert resp.status_code == 200
    nomes = [n.nome for n in resp.context["object_list"]]
    assert "N1" in nomes
    assert "N2" not in nomes


def test_nucleo_list_filtra_para_admin(client, organizacao, admin_user):
    other_org = Organizacao.objects.create(nome="Org2", cnpj="33.333.333/0003-33", slug="org3")
    Nucleo.objects.create(nome="N1", organizacao=organizacao)
    Nucleo.objects.create(nome="N2", organizacao=other_org)
    client.force_login(admin_user)
    resp = client.get(reverse("nucleos:list"))
    assert resp.status_code == 200
    nomes = [n.nome for n in resp.context["object_list"]]
    assert "N1" in nomes
    assert "N2" not in nomes


def test_nucleo_list_filtra_para_coordenador(client, organizacao):
    other_org = Organizacao.objects.create(nome="Org2", cnpj="44.444.444/0004-44", slug="org4")
    n1 = Nucleo.objects.create(nome="N1", organizacao=organizacao)
    Nucleo.objects.create(nome="N2", organizacao=organizacao)
    Nucleo.objects.create(nome="N3", organizacao=other_org)
    User = get_user_model()
    coord = User.objects.create_user(
        username="coord",
        email="coord@example.com",
        password="pwd",
        user_type=UserType.COORDENADOR,
        organizacao=organizacao,
    )
    ParticipacaoNucleo.objects.create(nucleo=n1, user=coord, status="ativo")
    client.force_login(coord)
    resp = client.get(reverse("nucleos:list"))
    assert resp.status_code == 200
    nomes = [n.nome for n in resp.context["object_list"]]
    assert "N1" in nomes
    assert "N2" not in nomes
    assert "N3" not in nomes
