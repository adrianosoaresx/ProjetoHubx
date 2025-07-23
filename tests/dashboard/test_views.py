import pytest
from django.urls import reverse
from django.contrib.auth.mixins import LoginRequiredMixin

from core.permissions import (
    AdminRequiredMixin,
    ClienteRequiredMixin,
    GerenteRequiredMixin,
    SuperadminRequiredMixin,
)
from dashboard.views import (
    DashboardBaseView,
    RootDashboardView,
    AdminDashboardView,
    GerenteDashboardView,
    ClienteDashboardView,
)

pytestmark = pytest.mark.django_db


def _assert_metrics_in_context(context):
    for key in [
        "num_users",
        "num_organizacoes",
        "num_nucleos",
        "num_empresas",
        "num_eventos",
    ]:
        assert key in context
        assert set(context[key].keys()) == {"total", "crescimento"}


def test_base_view_mixins():
    assert issubclass(DashboardBaseView, LoginRequiredMixin)


def test_view_mixins():
    assert issubclass(RootDashboardView, SuperadminRequiredMixin)
    assert issubclass(AdminDashboardView, AdminRequiredMixin)
    assert issubclass(GerenteDashboardView, GerenteRequiredMixin)
    assert issubclass(ClienteDashboardView, ClienteRequiredMixin)



def test_root_dashboard_view(client, root_user):
    client.force_login(root_user)
    resp = client.get(reverse("dashboard:root"))
    assert resp.status_code == 200
    assert "dashboard/root.html" in [t.name for t in resp.templates]
    _assert_metrics_in_context(resp.context)
    assert "Dashboard Root" in resp.content.decode()


def test_admin_dashboard_view(client, admin_user):
    client.force_login(admin_user)
    resp = client.get(reverse("dashboard:admin"))
    assert resp.status_code == 200
    assert "dashboard/admin.html" in [t.name for t in resp.templates]
    _assert_metrics_in_context(resp.context)
    assert "Dashboard Administrativo" in resp.content.decode()


def test_gerente_dashboard_view(client, gerente_user):
    client.force_login(gerente_user)
    resp = client.get(reverse("dashboard:gerente"))
    assert resp.status_code == 200
    assert "dashboard/gerente.html" in [t.name for t in resp.templates]
    _assert_metrics_in_context(resp.context)
    assert "Dashboard Gerente" in resp.content.decode()


def test_cliente_dashboard_view(client, cliente_user):
    client.force_login(cliente_user)
    resp = client.get(reverse("dashboard:cliente"))
    assert resp.status_code == 200
    assert "dashboard/cliente.html" in [t.name for t in resp.templates]
    _assert_metrics_in_context(resp.context)
    assert "Dashboard Cliente" in resp.content.decode()


def test_forbidden_dashboard_views(client, cliente_user):
    client.force_login(cliente_user)
    resp = client.get(reverse("dashboard:admin"))
    assert resp.status_code == 403
    resp = client.get(reverse("dashboard:root"))
    assert resp.status_code == 403

