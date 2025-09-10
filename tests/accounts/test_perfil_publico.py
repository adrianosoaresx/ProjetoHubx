import pytest
from django.urls import reverse

pytestmark = pytest.mark.django_db


def test_perfil_publico_respects_privacy(client, django_user_model):
    public_user = django_user_model.objects.create_user(email="pub@example.com", username="pub", password="pass")
    private_user = django_user_model.objects.create_user(
        email="priv@example.com", username="priv", password="pass", perfil_publico=False
    )

    resp = client.get(reverse("accounts:perfil_publico", args=[public_user.pk]))
    assert resp.status_code == 200

    resp_private = client.get(reverse("accounts:perfil_publico", args=[private_user.pk]))
    assert resp_private.status_code == 404
