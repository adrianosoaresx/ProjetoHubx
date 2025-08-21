import pytest
from django.contrib.auth import get_user_model
from django.test import override_settings
from django.urls import reverse
from django.utils import timezone
from freezegun import freeze_time

from accounts.models import SecurityEvent

User = get_user_model()


@pytest.mark.django_db
@override_settings(ROOT_URLCONF="tests.simple_urls")
@freeze_time("2024-01-01 12:00:00")
def test_delete_account_view(client):
    user = User.objects.create_user(email="del@example.com", username="del", password="pw")
    client.force_login(user)
    url = reverse("excluir_conta", urlconf="accounts.urls")
    resp = client.post(url, {"confirm": "EXCLUIR"})
    assert resp.status_code == 302
    user.refresh_from_db()
    assert user.deleted is True and user.deleted_at is not None
    assert user.exclusao_confirmada
    assert not user.is_active
    assert SecurityEvent.objects.filter(usuario=user, evento="conta_excluida").exists()
    token = user.account_tokens.get(tipo="cancel_delete")
    assert token.expires_at == timezone.now() + timezone.timedelta(days=30)


@pytest.mark.django_db
@override_settings(ROOT_URLCONF="tests.simple_urls")
def test_cancel_delete_view_reactivates_user(client):
    user = User.objects.create_user(email="view_cancel@example.com", username="view_cancel", password="pw")
    client.force_login(user)
    client.post(reverse("excluir_conta", urlconf="accounts.urls"), {"confirm": "EXCLUIR"})
    token = user.account_tokens.get(tipo="cancel_delete")
    resp = client.get(reverse("cancel_delete", args=[token.codigo], urlconf="accounts.urls"))
    assert resp.status_code == 200
    user.refresh_from_db()
    assert user.is_active
    assert not user.deleted and user.deleted_at is None
    assert not user.exclusao_confirmada
