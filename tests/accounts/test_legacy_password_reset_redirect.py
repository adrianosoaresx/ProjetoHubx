import pytest
from django.urls import reverse


@pytest.mark.django_db
def test_legacy_password_reset_redirects_to_confirm(client):
    response = client.get("/reset-password/?token=abc123")

    assert response.status_code == 302
    assert response.url == reverse("accounts:password_reset_confirm", args=["abc123"])


@pytest.mark.django_db
def test_legacy_password_reset_without_token_redirects_to_form(client):
    response = client.get("/reset-password/")

    assert response.status_code == 302
    assert response.url == reverse("accounts:password_reset")
