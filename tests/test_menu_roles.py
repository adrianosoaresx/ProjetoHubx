import pytest
from django.contrib.auth import get_user_model

from accounts.models import UserType


User = get_user_model()

PERFIL_URL = "/accounts/perfil/"
GERAR_CONVITE_URL = "/tokens/convites/gerar"
API_TOKENS_URL = "/tokens/api-tokens/"


@pytest.mark.django_db
def test_token_menu_visible_for_coordinator(client, settings):
    settings.ROOT_URLCONF = "Hubx.urls"
    user = User.objects.create_user(
        email="coordenador@example.com",
        username="coordenador",
        password="pass",
        user_type=UserType.COORDENADOR,
    )
    client.force_login(user)

    response = client.get(PERFIL_URL)
    assert GERAR_CONVITE_URL in response.content.decode()


@pytest.mark.django_db
@pytest.mark.parametrize("role", [UserType.ROOT, UserType.ADMIN])
def test_token_menu_hidden_for_root_and_admin(client, role, settings):
    settings.ROOT_URLCONF = "Hubx.urls"
    user = User.objects.create_user(
        email=f"{role.value}@example.com",
        username=role.value,
        password="pass",
        user_type=role,
    )
    client.force_login(user)

    response = client.get(PERFIL_URL)
    content = response.content.decode()
    assert GERAR_CONVITE_URL not in content
    assert API_TOKENS_URL not in content


@pytest.mark.django_db
@pytest.mark.parametrize(
    "role",
    [
        UserType.FINANCEIRO,
        UserType.NUCLEADO,
        UserType.ASSOCIADO,
        UserType.CONVIDADO,
    ],
)
def test_token_menu_hidden_for_other_roles(client, role, settings):
    settings.ROOT_URLCONF = "Hubx.urls"
    user = User.objects.create_user(
        email=f"{role.value}@example.com",
        username=role.value,
        password="pass",
        user_type=role,
    )
    client.force_login(user)

    response = client.get(PERFIL_URL)
    content = response.content.decode()
    assert GERAR_CONVITE_URL not in content
    assert API_TOKENS_URL not in content
