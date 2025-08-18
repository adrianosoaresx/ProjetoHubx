import pytest
from django.urls import reverse

pytestmark = pytest.mark.django_db


def test_metrics_partial_contains_required_cards(client, admin_user):
    client.force_login(admin_user)
    resp = client.get(reverse("dashboard:metrics-partial"))
    content = resp.content.decode()
    assert "Inscrições confirmadas" in content
    assert "Lançamentos pendentes" in content
