import json
from datetime import datetime, timedelta, timezone

import pytest

from ai_chat import services
from eventos.factories import EventoFactory
from nucleos.factories import NucleoFactory
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
    reference = datetime(2024, 5, 1, 12, 0, tzinfo=timezone.utc)
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
    assert result["data"][0]["period"].startswith("2024-05-01T12:00:00")
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
        "organizacao_id": other_org.id,
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

    assert result["organizacao_id"] == org.id
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

    assert result["organizacao_id"] == org.id
    assert [n["id"] for n in result["nucleos"]] == [str(active.id)]


@pytest.mark.django_db
def test_get_future_events_context_filters_by_org_and_nucleo():
    org = OrganizacaoFactory()
    other_org = OrganizacaoFactory()
    nucleo = NucleoFactory(organizacao=org)
    other_nucleo = NucleoFactory(organizacao=org)

    future_date = datetime.now(tz=timezone.utc) + timedelta(days=2)
    EventoFactory(organizacao=org, nucleo=nucleo, data_inicio=future_date)
    EventoFactory(organizacao=org, nucleo=other_nucleo, data_inicio=future_date)
    EventoFactory(organizacao=other_org, data_inicio=future_date)
    EventoFactory(organizacao=org, nucleo=nucleo, data_inicio=future_date - timedelta(days=5))

    result = services.get_future_events_context(org.id, nucleo_ids=[str(nucleo.id)])

    assert result["organizacao_id"] == org.id
    assert all(event["nucleo_id"] == str(nucleo.id) for event in result["events"])
    assert len(result["events"]) == 1
    assert json.loads(json.dumps(result))  # estrutura serializável
