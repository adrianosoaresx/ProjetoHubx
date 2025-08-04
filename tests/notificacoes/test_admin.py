import pytest
from django.urls import reverse
from django.core.exceptions import PermissionDenied
from django.contrib import admin

from accounts.factories import UserFactory
from notificacoes.models import NotificationLog, NotificationTemplate
from notificacoes.admin import NotificationLogAdmin

pytestmark = pytest.mark.django_db


def test_exportar_csv_admin(client):
    staff = UserFactory(is_staff=True, is_superuser=True)
    client.force_login(staff)
    user = UserFactory()
    template = NotificationTemplate.objects.create(codigo="t", assunto="a", corpo="b", canal="email")
    log = NotificationLog.objects.create(user=user, template=template, canal="email")
    url = reverse("admin:notificacoes_notificationlog_changelist")
    response = client.post(url, {"action": "exportar_csv", "_selected_action": [log.pk]})
    assert response.status_code == 200
    content = response.content.decode()
    assert "data_envio" in content.splitlines()[0]


def test_exportar_csv_requires_staff(rf):
    admin_site = admin.site
    admin_instance = NotificationLogAdmin(NotificationLog, admin_site)
    request = rf.post("/")
    request.user = UserFactory(is_staff=False)
    queryset = NotificationLog.objects.none()
    with pytest.raises(PermissionDenied):
        admin_instance.exportar_csv(request, queryset)
