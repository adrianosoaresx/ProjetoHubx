import pytest
from django.urls import reverse

pytestmark = pytest.mark.django_db


def test_filter_form_accessible(client, admin_user):
    client.force_login(admin_user)
    resp = client.get(reverse("dashboard:admin"))
    content = resp.content.decode()
    assert '<label for="periodo"' in content
    assert 'aria-label="Aplicar filtros"' in content
