import pytest
from django.urls import reverse
from accounts.models import User

pytestmark = pytest.mark.django_db

def test_root_metrics_partial(client):
    root_user = User.objects.create_superuser(
        email="root@example.com",
        username="root",
        password="pass",
    )
    client.force_login(root_user)
    resp = client.get(reverse("dashboard:metrics-partial"))
    assert resp.status_code == 200
