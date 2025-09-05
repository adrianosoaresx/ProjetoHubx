import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse

from accounts.models import UserType

User = get_user_model()
PERFIL_URL = "/accounts/perfil/"


@pytest.mark.django_db
def test_admin_menu_contains_associados_and_financeiro(client, settings):
    settings.ROOT_URLCONF = "Hubx.urls"
    user = User.objects.create_user(
        email="admin@example.com", username="admin", password="pass", user_type=UserType.ADMIN
    )
    client.force_login(user)

    response = client.get(PERFIL_URL)
    content = response.content.decode()

    assert "Associados" in content
    assert reverse("financeiro:repasses") in content


@pytest.mark.django_db
def test_financeiro_menu_hides_associados(client, settings):
    settings.ROOT_URLCONF = "Hubx.urls"
    user = User.objects.create_user(
        email="fin@example.com", username="fin", password="pass", user_type=UserType.FINANCEIRO
    )
    client.force_login(user)

    response = client.get(PERFIL_URL)
    content = response.content.decode()

    assert reverse("financeiro:repasses") in content
    assert "Associados" not in content
