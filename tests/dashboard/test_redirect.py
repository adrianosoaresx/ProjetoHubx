import pytest
from django.urls import reverse

pytestmark = pytest.mark.django_db


def test_dashboard_redirect_root(client, root_user):
    client.force_login(root_user)
    resp = client.get(reverse("dashboard:dashboard"))
    assert resp.status_code == 302
    assert resp.url == reverse("dashboard:root")


def test_dashboard_redirect_admin(client, admin_user):
    client.force_login(admin_user)
    resp = client.get(reverse("dashboard:dashboard"))
    assert resp.status_code == 302
    assert resp.url == reverse("dashboard:admin")


def test_dashboard_redirect_coordenador(client, gerente_user):
    client.force_login(gerente_user)
    resp = client.get(reverse("dashboard:dashboard"))
    assert resp.status_code == 302
    assert resp.url == reverse("dashboard:coordenador")


def test_dashboard_redirect_cliente(client, cliente_user):
    client.force_login(cliente_user)
    resp = client.get(reverse("dashboard:dashboard"))
    assert resp.status_code == 302
    assert resp.url == reverse("dashboard:cliente")


def test_dashboard_redirect_nucleado(client, nucleado_user):
    client.force_login(nucleado_user)
    resp = client.get(reverse("dashboard:dashboard"))
    assert resp.status_code == 302
    assert resp.url == reverse("dashboard:cliente")


def test_dashboard_redirect_unknown_type(client, convidado_user):
    client.force_login(convidado_user)
    resp = client.get(reverse("dashboard:dashboard"))
    assert resp.status_code == 302
    assert resp.url == reverse("accounts:perfil")


def test_dashboard_redirect_anonymous(client):
    resp = client.get(reverse("dashboard:dashboard"))
    assert resp.status_code == 302
    assert reverse("accounts:login") in resp.url
