import pytest
from django.contrib.auth.models import Permission
from django.http import HttpResponse
from django.urls import reverse
from unittest.mock import patch

from accounts.factories import UserFactory


pytestmark = pytest.mark.django_db


def test_list_templates_requires_view_permission(client):
    user = UserFactory()
    client.force_login(user)

    url = reverse("notificacoes:templates_list")

    response = client.get(url)
    assert response.status_code == 403

    perm = Permission.objects.get(codename="view_notificationtemplate")
    user.user_permissions.add(perm)

    with patch("notificacoes.views.render", return_value=HttpResponse("OK")):
        response = client.get(url)
    assert response.status_code == 200
