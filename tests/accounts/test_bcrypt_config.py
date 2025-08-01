import pytest
from django.conf import settings
from django.contrib.auth import get_user_model


@pytest.mark.django_db
def test_bcrypt_is_default_hasher():
    assert settings.PASSWORD_HASHERS[0] == "django.contrib.auth.hashers.BCryptSHA256PasswordHasher"
    assert settings.BCRYPT_ROUNDS >= 12
    user = get_user_model().objects.create_user(email="x@example.com", username="x", password="123")
    assert user.password.startswith("bcrypt_sha256$")
