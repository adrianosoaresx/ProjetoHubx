import pyotp
import pytest
from django.contrib.auth import authenticate, get_user_model

User = get_user_model()


@pytest.mark.django_db
def test_totp_login():
    user = User.objects.create_user(
        email="x@example.com",
        username="x",
        password="pass",
        two_factor_enabled=True,
        two_factor_secret=pyotp.random_base32(),
    )
    totp = pyotp.TOTP(user.two_factor_secret).now()
    assert (
        authenticate(
            username="x@example.com",
            password="pass",
            totp=totp,
            backend="accounts.backends.EmailBackend",
        )
        == user
    )
