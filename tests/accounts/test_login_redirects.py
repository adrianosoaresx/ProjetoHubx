import os

import django
import pyotp
import pytest
from django.contrib.auth import get_user_model
from django.test import Client
from django.urls import reverse

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "Hubx.settings")
django.setup()

from tokens.models import TOTPDevice  # noqa: E402




@pytest.mark.django_db
def test_login_get_sem_next_renderiza_formulario() -> None:
    client = Client()

    response = client.get(reverse("accounts:login"))

    assert response.status_code == 200

@pytest.mark.django_db
def test_login_simples_redireciona_para_next_valido() -> None:
    user_model = get_user_model()
    senha = "senha123forte"
    user_model.objects.create_user(
        username="usuario.simples",
        email="simples@example.com",
        password=senha,
    )

    client = Client()
    next_url = "/eventos/evento/11111111-1111-1111-1111-111111111111/inscricao/overview/"

    response = client.post(
        reverse("accounts:login"),
        {"email": "simples@example.com", "password": senha, "next": next_url},
    )

    assert response.status_code == 302
    assert response.url == next_url


@pytest.mark.django_db
def test_login_com_2fa_preserva_destino_da_primeira_etapa() -> None:
    user_model = get_user_model()
    senha = "senha123forte"
    secret = pyotp.random_base32()
    user = user_model.objects.create_user(
        username="usuario.2fa",
        email="twofa@example.com",
        password=senha,
        two_factor_enabled=True,
        two_factor_secret=secret,
    )
    TOTPDevice.objects.create(usuario=user, secret=secret, confirmado=True)

    client = Client()
    next_url = "/eventos/evento/22222222-2222-2222-2222-222222222222/inscricao/overview/"

    login_response = client.post(
        reverse("accounts:login"),
        {"email": "twofa@example.com", "password": senha, "next": next_url},
    )

    assert login_response.status_code == 302
    assert login_response.url == reverse("accounts:login_totp")

    session = client.session
    assert session.get("pending_2fa_next_url") == next_url

    totp_response = client.post(
        reverse("accounts:login_totp"),
        {"totp": pyotp.TOTP(secret).now()},
    )

    assert totp_response.status_code == 302
    assert totp_response.url == next_url

    session = client.session
    assert "pending_2fa_user_id" not in session
    assert "pending_2fa_next_url" not in session


@pytest.mark.django_db
def test_next_externo_e_descartado_com_fallback_para_perfil() -> None:
    user_model = get_user_model()
    senha = "senha123forte"
    user_model.objects.create_user(
        username="usuario.externo",
        email="externo@example.com",
        password=senha,
    )

    client = Client()

    response = client.post(
        reverse("accounts:login"),
        {
            "email": "externo@example.com",
            "password": senha,
            "next": "https://evil.example.com/roubo",
        },
    )

    assert response.status_code == 302
    assert response.url == reverse("accounts:perfil")
