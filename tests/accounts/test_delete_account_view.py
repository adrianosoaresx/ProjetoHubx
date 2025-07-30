import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone

from accounts.models import SecurityEvent

User = get_user_model()


@pytest.mark.django_db
def test_delete_account_view(client):
    user = User.objects.create_user(email="del@example.com", username="del", password="pw")
    client.force_login(user)
    url = reverse("accounts:excluir_conta")
    resp = client.post(url, {"confirm": "EXCLUIR"})
    assert resp.status_code == 302
    user.refresh_from_db()
    assert user.deleted_at is not None
    assert user.exclusao_confirmada
    assert not user.is_active
    assert SecurityEvent.objects.filter(usuario=user, evento="conta_excluida").exists()
