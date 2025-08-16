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

