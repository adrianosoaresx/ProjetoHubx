import pytest
from django.urls import reverse

pytestmark = pytest.mark.urls("tests.dashboard.urls")


@pytest.mark.django_db
@pytest.mark.parametrize(
    "url_name",
    [
        "dashboard:config-create",
        "dashboard:filter-create",
        "dashboard:layout-create",
    ],
)
def test_publico_field_visible_for_admin(client, admin_user, url_name):
    client.force_login(admin_user)
    resp = client.get(reverse(url_name))
    assert "id_publico" in resp.content.decode()


@pytest.mark.django_db
@pytest.mark.parametrize(
    "url_name",
    [
        "dashboard:config-create",
        "dashboard:filter-create",
        "dashboard:layout-create",
    ],
)
def test_publico_field_hidden_for_non_admin(client, cliente_user, url_name):
    client.force_login(cliente_user)
    resp = client.get(reverse(url_name))
    content = resp.content.decode()
    assert "id_publico" not in content
    assert "Apenas administradores podem publicar itens" in content
