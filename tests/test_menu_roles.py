import pytest
from django.contrib.auth import get_user_model

from accounts.models import UserType


User = get_user_model()

PERFIL_URL = "/accounts/perfil/"
CONVITES_LIST_URL = "/tokens/convites/"
GERAR_CONVITE_URL = "/tokens/convites/gerar"


@pytest.mark.django_db
@pytest.mark.parametrize(
    "role,expected",
    [
        (UserType.ROOT, CONVITES_LIST_URL),
        (UserType.ADMIN, CONVITES_LIST_URL),
    ],
)
def test_token_menu_visible_for_roles(client, role, expected, settings):
    settings.ROOT_URLCONF = "Hubx.urls"
    user = User.objects.create_user(
        email=f"{role.value}@example.com", username=role.value, password="pass", user_type=role
    )
    client.force_login(user)

    response = client.get(PERFIL_URL)
    assert expected in response.content.decode()


@pytest.mark.django_db
@pytest.mark.parametrize(
    "role",
    [
        UserType.NUCLEADO,
        UserType.ASSOCIADO,
        UserType.CONVIDADO,
    ],
)
def test_token_menu_hidden_for_other_roles(client, role, settings):
    settings.ROOT_URLCONF = "Hubx.urls"
    user = User.objects.create_user(
        email=f"{role.value}@example.com", username=role.value, password="pass", user_type=role
    )
    client.force_login(user)

    response = client.get(PERFIL_URL)
    content = response.content.decode()
    assert CONVITES_LIST_URL not in content
    assert GERAR_CONVITE_URL not in content
