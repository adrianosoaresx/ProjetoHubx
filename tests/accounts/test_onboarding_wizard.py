from __future__ import annotations

import pytest
from django.urls import reverse
from django.utils import timezone

from accounts.models import AccountToken, User
from tokens.factories import TokenAcessoFactory


@pytest.mark.django_db
def test_onboarding_wizard_flow(client, mocker):
    convite = TokenAcessoFactory(
        estado="novo",
        data_expiracao=timezone.now() + timezone.timedelta(hours=1),
    )
    mocker.patch("accounts.tasks.send_confirmation_email.delay")
    mocker.patch("accounts.views.login")
    session = client.session
    session["invite_token"] = convite.codigo
    session.save()

    resp = client.post(reverse("accounts:usuario"), {"usuario": "wizard"})
    assert resp.status_code == 302
    resp = client.post(reverse("accounts:nome"), {"nome": "Wizard Test"})
    assert resp.status_code == 302
    resp = client.post(reverse("accounts:cpf"), {"cpf": "123.456.789-00"})
    assert resp.status_code == 302
    resp = client.post(reverse("accounts:email"), {"email": "wizard@example.com"})
    assert resp.status_code == 302
    resp = client.post(
        reverse("accounts:senha"),
        {"senha": "Strong123!", "confirmar_senha": "Strong123!"},
    )
    assert resp.status_code == 302
    resp = client.post(reverse("accounts:foto"))
    assert resp.status_code == 302
    resp = client.post(reverse("accounts:termos"), {"aceitar_termos": "on"})
    assert resp.status_code == 302

    user = User.objects.get(username="wizard")
    assert not user.is_active
    assert AccountToken.objects.filter(
        usuario=user, tipo=AccountToken.Tipo.EMAIL_CONFIRMATION
    ).exists()


@pytest.mark.django_db
def test_onboarding_requires_token(client):
    resp = client.post(reverse("accounts:usuario"), {"usuario": "x"})
    assert resp.status_code == 302
    assert resp.url == reverse("tokens:token")


@pytest.mark.django_db
def test_onboarding_validates_cpf_and_email(client, mocker):
    convite = TokenAcessoFactory(
        estado="novo",
        data_expiracao=timezone.now() + timezone.timedelta(hours=1),
    )
    existing = User.objects.create_user(
        email="existing@example.com", username="exist", cpf="123.456.789-00"
    )
    mocker.patch("accounts.tasks.send_confirmation_email.delay")
    session = client.session
    session["invite_token"] = convite.codigo
    session.save()
    client.post(reverse("accounts:usuario"), {"usuario": "wizard"})
    client.post(reverse("accounts:nome"), {"nome": "Wizard Test"})
    resp = client.post(reverse("accounts:cpf"), {"cpf": existing.cpf})
    assert resp.status_code == 200
    assert "cpf" not in client.session
    resp = client.post(reverse("accounts:cpf"), {"cpf": "123.456.789-99"})
    assert resp.status_code == 302
    resp = client.post(reverse("accounts:email"), {"email": existing.email})
    assert resp.status_code == 200
    assert "email" not in client.session


@pytest.mark.django_db
def test_onboarding_terms_required(client, mocker):
    convite = TokenAcessoFactory(
        estado="novo",
        data_expiracao=timezone.now() + timezone.timedelta(hours=1),
    )
    mocker.patch("accounts.tasks.send_confirmation_email.delay")
    session = client.session
    session["invite_token"] = convite.codigo
    session.save()
    client.post(reverse("accounts:usuario"), {"usuario": "wizard"})
    client.post(reverse("accounts:nome"), {"nome": "Wizard Test"})
    client.post(reverse("accounts:cpf"), {"cpf": "111.222.333-44"})
    client.post(reverse("accounts:email"), {"email": "wizard@example.com"})
    client.post(reverse("accounts:senha"), {"senha": "Strong123!", "confirmar_senha": "Strong123!"})
    client.post(reverse("accounts:foto"))
    resp = client.post(reverse("accounts:termos"))
    assert resp.status_code == 200
    assert not User.objects.filter(username="wizard").exists()

