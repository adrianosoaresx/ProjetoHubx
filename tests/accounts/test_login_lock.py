import pytest
from django.contrib.auth import authenticate, get_user_model
from django.utils import timezone

User = get_user_model()


@pytest.mark.django_db
def test_login_lock(monkeypatch):
    user = User.objects.create_user(email="lock@example.com", username="l", password="pass")
    for _ in range(3):
        assert authenticate(username="lock@example.com", password="wrong") is None
    user.refresh_from_db()
    assert user.lock_expires_at is not None
    monkeypatch.setattr(timezone, "now", lambda: user.lock_expires_at + timezone.timedelta(seconds=1))
    assert authenticate(username="lock@example.com", password="pass") == user
