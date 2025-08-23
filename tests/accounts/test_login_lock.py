import pytest
from django.contrib.auth import authenticate, get_user_model
from django.utils import timezone
from django.core.cache import cache

User = get_user_model()


@pytest.mark.django_db
def test_login_lock(monkeypatch):
    user = User.objects.create_user(email="lock@example.com", username="l", password="pass")
    for _ in range(3):
        assert authenticate(username="lock@example.com", password="wrong") is None
    lock_key = f"lockout_user_{user.pk}"
    lock_until = cache.get(lock_key)
    assert lock_until is not None
    monkeypatch.setattr(timezone, "now", lambda: lock_until + timezone.timedelta(seconds=1))
    assert authenticate(username="lock@example.com", password="pass") == user
