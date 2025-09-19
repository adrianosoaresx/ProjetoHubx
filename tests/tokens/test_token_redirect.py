import pytest
from django.urls import reverse

from accounts.factories import UserFactory
from accounts.models import UserType

pytestmark = pytest.mark.django_db


@pytest.mark.parametrize("user_type", [UserType.ROOT.value, UserType.ADMIN.value])
def test_root_admin_redirect_to_gerar_convite(client, user_type):
    user = UserFactory(user_type=user_type)
    client.force_login(user)

    resp = client.get(reverse("tokens:token"))
    assert resp.status_code == 302
    assert resp.url == reverse("tokens:gerar_convite")
