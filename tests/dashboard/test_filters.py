import pytest
from django.urls import reverse

from audit.models import AuditLog
from dashboard.models import DashboardFilter

pytestmark = pytest.mark.urls("tests.dashboard.urls")


@pytest.mark.django_db
def test_filter_crud_with_audit(client, admin_user):
    client.force_login(admin_user)
    url = reverse("dashboard:filter-create") + "?periodo=mensal"
    resp = client.post(url, {"nome": "F1", "publico": False})
    assert resp.status_code == 302
    filtro = DashboardFilter.objects.get(nome="F1")
    assert AuditLog.objects.filter(action="CREATE_FILTER", object_id=str(filtro.pk)).exists()

    url_edit = reverse("dashboard:filter-edit", args=[filtro.pk]) + "?periodo=anual"
    resp = client.post(url_edit, {"nome": "F2", "publico": True})
    assert resp.status_code == 302
    filtro.refresh_from_db()
    assert filtro.nome == "F2"
    assert AuditLog.objects.filter(action="UPDATE_FILTER", object_id=str(filtro.pk)).exists()

    resp = client.post(reverse("dashboard:filter-delete", args=[filtro.pk]))
    assert resp.status_code == 302
    assert not DashboardFilter.objects.filter(pk=filtro.pk).exists()
    assert AuditLog.objects.filter(action="DELETE_FILTER", object_id=str(filtro.pk)).exists()

