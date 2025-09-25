import re

import pytest
from django.urls import reverse

from accounts.factories import UserFactory
from accounts.models import UserType


pytestmark = pytest.mark.django_db


@pytest.fixture
def admin_user():
    user = UserFactory()
    user.user_type = UserType.ADMIN
    user.save()
    return user


@pytest.fixture
def client_logged(client, admin_user):
    client.force_login(admin_user)
    return client


def test_importar_pagamentos_template_messages(client_logged):
    response = client_logged.get(reverse("financeiro:importar_pagamentos"))
    assert response.status_code == 200
    html = response.content.decode()
    assert "importação automática foi desativada" in html
    assert "Envie o arquivo CSV" in html
