import pytest
from django.urls import reverse
from django.contrib.auth.models import Permission

from accounts.factories import UserFactory
from notificacoes.models import NotificationTemplate


pytestmark = pytest.mark.django_db


def test_toggle_template(client):
    user = UserFactory()
    perm = Permission.objects.get(codename="change_notificationtemplate")
    user.user_permissions.add(perm)
    client.force_login(user)

    template = NotificationTemplate.objects.create(
        codigo="t1", assunto="a", corpo="b", canal="email", ativo=True
    )

    url = reverse("notificacoes:template_toggle", args=[template.codigo])
    response = client.post(url)
    assert response.status_code == 302
    template.refresh_from_db()
    assert template.ativo is False

    response = client.post(url)
    template.refresh_from_db()
    assert template.ativo is True
