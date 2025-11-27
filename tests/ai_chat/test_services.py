import json
from datetime import datetime, timedelta, timezone as dt_timezone

import pytest
from django.utils import timezone

from ai_chat import services
from accounts.factories import UserFactory
from eventos.models import InscricaoEvento
from eventos.factories import EventoFactory
from nucleos.factories import NucleoFactory
from nucleos.models import ParticipacaoNucleo
from organizacoes.factories import OrganizacaoFactory


@pytest.mark.django_db
def test_get_membership_totals_calls_dependencies(monkeypatch):
    calls: dict[str, object] = {}

    def fake_calculate(org_id: str):
        calls["calc"] = org_id
        return {"ativos": 5}

    def fake_chart(totals):
        calls["chart"] = totals
        return {"figure": {"data": []}}

    monkeypatch.setattr(services, "calculate_membership_totals", fake_calculate)
    monkeypatch.setattr(services, "build_chart_payload", fake_chart)

    result = services.get_membership_totals("org-1")

    assert calls == {"calc": "org-1", "chart": {"ativos": 5}}
    assert result == {
        "organizacao_id": "org-1",
        "totals": {"ativos": 5},
        "chart": {"figure": {"data": []}},
    }


@pytest.mark.django_db
def test_get_event_status_totals_calls_dependencies(monkeypatch):
    calls: dict[str, object] = {}

    def fake_calculate(org_id: str):
        calls["calc"] = org_id
        return {"aberto": 3, "fechado": 1}

    def fake_chart(totals):
        calls["chart"] = totals
        return {"figure": {"layout": {}}}

    monkeypatch.setattr(services, "calculate_event_status_totals", fake_calculate)
    monkeypatch.setattr(services, "build_chart_payload", fake_chart)

    result = services.get_event_status_totals("org-2")

    assert calls == {"calc": "org-2", "chart": {"aberto": 3, "fechado": 1}}
    assert result == {
        "organizacao_id": "org-2",
        "totals": {"aberto": 3, "fechado": 1},
        "chart": {"figure": {"layout": {}}},
    }


@pytest.mark.django_db
def test_get_monthly_members_serializes_dates(monkeypatch):
    reference = datetime(2024, 5, 1, 12, 0, tzinfo=dt_timezone.utc)
    data_points = [
        {"period": reference, "total": 2, "std_dev": 0.1},
        {"period": reference - timedelta(days=30), "total": 1, "std_dev": 0.2},
    ]
    calls: dict[str, object] = {}

    def fake_calculate(org_id: str, months: int, reference: datetime | None = None):
        calls["calc"] = (org_id, months, reference)
        return data_points

    def fake_chart(points, **kwargs):
        calls["chart"] = {"points": points, **kwargs}
        return {"figure": {"data": [1]}}

    monkeypatch.setattr(services, "calculate_monthly_membros", fake_calculate)
    monkeypatch.setattr(services, "build_time_series_chart", fake_chart)

    result = services.get_monthly_members("org-3", months=6, reference=reference)

    assert calls["calc"] == ("org-3", 6, reference)
    assert calls["chart"]["points"] == data_points
    assert result["data"][0]["period"].startswith("2024-05-01")
    assert result["months"] == 6
    assert result["chart"] == {"figure": {"data": [1]}}


@pytest.mark.django_db
def test_get_nucleo_metrics_filters_by_organizacao(monkeypatch):
    org = OrganizacaoFactory()
    other_org = OrganizacaoFactory()
    nucleo = NucleoFactory(organizacao=org)

    def unexpected_call(*args, **kwargs):  # pragma: no cover - defesa
        raise AssertionError("Métricas não deveriam ser chamadas")

    monkeypatch.setattr(services.nucleos_metrics, "get_total_membros", unexpected_call)

    result = services.get_nucleo_metrics(other_org.id, str(nucleo.id))

    assert result == {
        "organizacao_id": str(other_org.id),
        "nucleo_id": str(nucleo.id),
        "error": "Núcleo não encontrado para a organização.",
    }


@pytest.mark.django_db
def test_get_nucleo_metrics_returns_context(monkeypatch):
    org = OrganizacaoFactory()
    nucleo = NucleoFactory(organizacao=org)

    monkeypatch.setattr(services.nucleos_metrics, "get_total_membros", lambda nucleo_id: 10)
    monkeypatch.setattr(services.nucleos_metrics, "get_total_suplentes", lambda nucleo_id: 2)
    monkeypatch.setattr(
        services.nucleos_metrics, "get_membros_por_status", lambda nucleo_id: {"ativo": 8}
    )
    monkeypatch.setattr(
        services.nucleos_metrics, "get_taxa_participacao", lambda organizacao_id: 0.75
    )

    result = services.get_nucleo_metrics(org.id, str(nucleo.id))

    assert result["organizacao_id"] == str(org.id)
    assert result["nucleo"]["id"] == str(nucleo.id)
    assert result["total_membros"] == 10
    assert result["membros_por_status"] == {"ativo": 8}
    assert result["taxa_participacao"] == 0.75


@pytest.mark.django_db
def test_get_organizacao_description_returns_fields():
    org = OrganizacaoFactory(nome="Org Teste", descricao="Desc")
    OrganizacaoFactory()  # outra organização que não deve influenciar

    result = services.get_organizacao_description(org.id)

    assert result["id"] == org.id
    assert result["nome"] == "Org Teste"
    assert result["descricao"] == "Desc"
    assert "error" not in result


@pytest.mark.django_db
def test_get_organizacao_description_missing():
    result = services.get_organizacao_description("missing-id")

    assert result == {"organizacao_id": "missing-id", "error": "Organização não encontrada."}


@pytest.mark.django_db
def test_get_organizacao_nucleos_context_filters_actives():
    org = OrganizacaoFactory()
    active = NucleoFactory(organizacao=org, ativo=True)
    NucleoFactory(organizacao=org, ativo=False)
    NucleoFactory()  # outra organização

    result = services.get_organizacao_nucleos_context(org.id)

    assert result["organizacao_id"] == str(org.id)
    assert [n["id"] for n in result["nucleos"]] == [str(active.id)]


@pytest.mark.django_db
def test_get_future_events_context_filters_by_org_and_nucleo():
    org = OrganizacaoFactory()
    other_org = OrganizacaoFactory()
    nucleo = NucleoFactory(organizacao=org)
    other_nucleo = NucleoFactory(organizacao=org)

    future_date = timezone.now() + timedelta(days=2)
    EventoFactory(organizacao=org, nucleo=nucleo, data_inicio=future_date)
    EventoFactory(organizacao=org, nucleo=other_nucleo, data_inicio=future_date)
    EventoFactory(organizacao=other_org, data_inicio=future_date)
    EventoFactory(organizacao=org, nucleo=nucleo, data_inicio=future_date - timedelta(days=5))

    result = services.get_future_events_context(org.id, nucleo_ids=[str(nucleo.id)])

    assert result["organizacao_id"] == str(org.id)
    assert all(event["nucleo_id"] == str(nucleo.id) for event in result["events"])
    assert len(result["events"]) == 1
    assert json.loads(json.dumps(result))  # estrutura serializável


@pytest.mark.django_db
def test_get_organizacao_nucleos_context_limits_to_user_participations():
    org = OrganizacaoFactory()
    user = UserFactory(organizacao=org)
    consultor_nucleo = NucleoFactory(organizacao=org, consultor=user)
    membro_nucleo = NucleoFactory(organizacao=org)
    ParticipacaoNucleo.objects.create(
        user=user,
        nucleo=membro_nucleo,
        status="ativo",
        papel="membro",
    )
    NucleoFactory(organizacao=org)  # núcleo sem vínculo

    result = services.get_organizacao_nucleos_context(org.id, usuario_id=str(user.id))

    assert set(nucleo["id"] for nucleo in result["nucleos"]) == {
        str(consultor_nucleo.id),
        str(membro_nucleo.id),
    }


@pytest.mark.django_db
def test_get_future_events_context_limits_to_user_nucleos():
    org = OrganizacaoFactory()
    user = UserFactory(organizacao=org)
    nucleo = NucleoFactory(organizacao=org)
    ParticipacaoNucleo.objects.create(
        user=user,
        nucleo=nucleo,
        status="ativo",
        papel="membro",
    )
    other_nucleo = NucleoFactory(organizacao=org)

    future_date = timezone.now() + timedelta(days=2)
    EventoFactory(organizacao=org, nucleo=nucleo, data_inicio=future_date)
    EventoFactory(organizacao=org, nucleo=other_nucleo, data_inicio=future_date)

    result = services.get_future_events_context(org.id, usuario_id=str(user.id))

    assert [event["nucleo_id"] for event in result["events"]] == [str(nucleo.id)]


@pytest.mark.django_db
def test_get_associados_list_filters_and_sanitizes(cache):
    org = OrganizacaoFactory()
    other_org = OrganizacaoFactory()
    viewer = UserFactory(organizacao=org)
    active = UserFactory(
        organizacao=org, is_associado=True, username="ativo", contato="A Ativo"
    )
    second = UserFactory(
        organizacao=org, is_associado=True, username="beta", contato="B Beta"
    )
    UserFactory(organizacao=org, is_associado=True, is_active=False)
    UserFactory(organizacao=other_org, is_associado=True)

    result = services.get_associados_list(
        org.id, usuario_id=str(viewer.id), limit=1, offset=0
    )

    assert result["organizacao_id"] == str(org.id)
    assert [item["id"] for item in result["associados"]] == [str(active.id)]
    assert "email" not in json.dumps(result)


@pytest.mark.django_db
def test_get_associados_list_requires_same_organization(cache):
    org = OrganizacaoFactory()
    UserFactory(organizacao=org, is_associado=True)
    outsider = UserFactory()

    result = services.get_associados_list(org.id, usuario_id=str(outsider.id), limit=1)

    assert result["associados"] == []
    assert "error" in result


@pytest.mark.django_db
def test_get_nucleados_list_respects_org_and_status():
    org = OrganizacaoFactory()
    nucleo = NucleoFactory(organizacao=org)
    other_nucleo = NucleoFactory(organizacao=org)
    membro = UserFactory(organizacao=org, is_associado=True, contato="A")
    outro_membro = UserFactory(organizacao=org, is_associado=True, contato="B")
    outro = UserFactory(organizacao=org, is_associado=True)

    ParticipacaoNucleo.objects.create(
        user=membro,
        nucleo=nucleo,
        status="ativo",
        papel="membro",
    )
    ParticipacaoNucleo.objects.create(
        user=outro_membro,
        nucleo=nucleo,
        status="ativo",
        papel="membro",
    )
    ParticipacaoNucleo.objects.create(
        user=outro,
        nucleo=other_nucleo,
        status="pendente",
        papel="membro",
    )

    result = services.get_nucleados_list(
        org.id, str(nucleo.id), usuario_id=str(membro.id), limit=1, offset=1
    )

    assert result["organizacao_id"] == str(org.id)
    assert [item["id"] for item in result["nucleados"]] == [str(outro_membro.id)]
    assert all(n["status"] == "ativo" for n in result["nucleados"])


@pytest.mark.django_db
def test_get_nucleados_list_requires_permission():
    org = OrganizacaoFactory()
    nucleo = NucleoFactory(organizacao=org)
    ParticipacaoNucleo.objects.create(
        user=UserFactory(organizacao=org, is_associado=True),
        nucleo=nucleo,
        status="ativo",
        papel="membro",
    )

    outsider = UserFactory()

    result = services.get_nucleados_list(
        org.id, str(nucleo.id), usuario_id=str(outsider.id), limit=1
    )

    assert result["nucleados"] == []
    assert "error" in result


@pytest.mark.django_db
def test_get_nucleos_list_returns_only_active():
    org = OrganizacaoFactory()
    active = NucleoFactory(organizacao=org, ativo=True)
    NucleoFactory(organizacao=org, ativo=False)
    NucleoFactory()  # outra organização

    result = services.get_nucleos_list(org.id)

    assert [n["id"] for n in result["nucleos"]] == [str(active.id)]


@pytest.mark.django_db
def test_get_eventos_list_filters_future_only():
    org = OrganizacaoFactory()
    past = EventoFactory(organizacao=org, data_inicio=timezone.now() - timedelta(days=2))
    future = EventoFactory(organizacao=org, data_inicio=timezone.now() + timedelta(days=2))

    future_only = services.get_eventos_list(org.id, future_only=True, limit=1)
    all_events = services.get_eventos_list(org.id, future_only=False, limit=2)

    assert [e["id"] for e in future_only["eventos"]] == [str(future.id)]
    assert set(e["id"] for e in all_events["eventos"]) == {str(past.id), str(future.id)}


@pytest.mark.django_db
def test_get_inscritos_list_returns_names(cache):
    evento = EventoFactory()
    associado = UserFactory(organizacao=evento.organizacao, is_associado=True, contato="Nome Teste")
    ParticipacaoNucleo.objects.create(user=associado, nucleo=evento.nucleo, status="ativo")
    InscricaoEvento.objects.create(user=associado, evento=evento, status="confirmada")
    outro_associado = UserFactory(
        organizacao=evento.organizacao, is_associado=True, contato="Outro Nome"
    )
    ParticipacaoNucleo.objects.create(
        user=outro_associado, nucleo=evento.nucleo, status="ativo"
    )
    InscricaoEvento.objects.create(
        user=outro_associado, evento=evento, status="confirmada"
    )
    InscricaoEvento.objects.create(
        user=UserFactory(organizacao=evento.organizacao),
        evento=EventoFactory(organizacao=evento.organizacao),
        status="confirmada",
    )

    result = services.get_inscritos_list(
        str(evento.id), usuario_id=str(associado.id), limit=1, offset=0
    )

    assert result["evento_id"] == str(evento.id)
    assert result["inscritos"] == [{"id": str(associado.id), "nome": "Nome Teste"}]


@pytest.mark.django_db
def test_get_inscritos_list_requires_access(cache):
    evento = EventoFactory()
    inscrito = UserFactory(organizacao=evento.organizacao, is_associado=True)
    ParticipacaoNucleo.objects.create(user=inscrito, nucleo=evento.nucleo, status="ativo")
    InscricaoEvento.objects.create(user=inscrito, evento=evento, status="confirmada")

    outsider = UserFactory()

    result = services.get_inscritos_list(str(evento.id), usuario_id=str(outsider.id))

    assert result["inscritos"] == []
    assert "error" in result
