import os

import django
import pytest
from django.contrib.auth import get_user_model

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "Hubx.settings")
django.setup()

from tokens.models import TOTPDevice  # noqa: E402


@pytest.mark.django_db
def test_two_factor_secret_and_totp_secret_persistem_valor_cifrado_longo() -> None:
    user_model = get_user_model()
    secret = "A" * 320

    user = user_model.objects.create_user(
        username="usuario.encrypted.secret",
        email="encrypted.secret@example.com",
        password="senha123forte",
        two_factor_secret=secret,
    )
    TOTPDevice.objects.create(usuario=user, secret=secret, confirmado=True)

    user.refresh_from_db()
    device = TOTPDevice.objects.get(usuario=user)

    assert user.two_factor_secret == secret
    assert device.secret == secret
