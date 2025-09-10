from __future__ import annotations

import pytest
from django.test import Client
from django.urls import reverse
from django.utils import timezone

from accounts.models import AccountToken, User
from tokens.factories import TokenAcessoFactory
from tokens.models import TokenAcesso
import hashlib


@pytest.mark.django_db
def test_onboarding_wizard_flow(client, monkeypatch):
    convite = TokenAcessoFactory(
        estado="novo",
        data_expiracao=timezone.now() + timezone.timedelta(hours=1),
    )
    monkeypatch.setattr("accounts.tasks.send_confirmation_email.delay", lambda *args, **kwargs: None)
    monkeypatch.setattr("accounts.views.login", lambda *args, **kwargs: None)
    original_get = TokenAcesso.objects.get

    def get_with_codigo(*args, **kwargs):
        codigo = kwargs.pop("codigo", None)
        if codigo is not None:
            kwargs["codigo_hash"] = hashlib.sha256(codigo.encode()).hexdigest()
        return original_get(*args, **kwargs)

    monkeypatch.setattr(TokenAcesso.objects, "get", get_with_codigo)
    session = client.session
    session["invite_token"] = convite.codigo
    session.save()

    resp = client.post(reverse("accounts:usuario"), {"usuario": "wizard"})
    assert resp.status_code == 302
    resp = client.post(reverse("accounts:nome"), {"nome": "Wizard Test"})
    assert resp.status_code == 302
    resp = client.post(reverse("accounts:cpf"), {"cpf": "123.456.789-09"})
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
    assert AccountToken.objects.filter(usuario=user, tipo=AccountToken.Tipo.EMAIL_CONFIRMATION).exists()


@pytest.mark.django_db
def test_onboarding_concurrent_username(client, monkeypatch):
    convite1 = TokenAcessoFactory(
        estado="novo",
        data_expiracao=timezone.now() + timezone.timedelta(hours=1),
    )
    convite2 = TokenAcessoFactory(
        estado="novo",
        data_expiracao=timezone.now() + timezone.timedelta(hours=1),
    )
    monkeypatch.setattr("accounts.tasks.send_confirmation_email.delay", lambda *args, **kwargs: None)
    monkeypatch.setattr("accounts.views.login", lambda *args, **kwargs: None)
    original_get = TokenAcesso.objects.get

    def get_with_codigo(*args, **kwargs):
        codigo = kwargs.pop("codigo", None)
        if codigo is not None:
            kwargs["codigo_hash"] = hashlib.sha256(codigo.encode()).hexdigest()
        return original_get(*args, **kwargs)

    monkeypatch.setattr(TokenAcesso.objects, "get", get_with_codigo)

    client1 = client
    client2 = Client()

    for cl, convite in ((client1, convite1), (client2, convite2)):
        session = cl.session
        session["invite_token"] = convite.codigo
        session.save()

    resp = client1.post(reverse("accounts:usuario"), {"usuario": "wizard"})
    assert resp.status_code == 302
    resp = client2.post(reverse("accounts:usuario"), {"usuario": "wizard"})
    assert resp.status_code == 302

    client1.post(reverse("accounts:nome"), {"nome": "Wizard One"})
    client2.post(reverse("accounts:nome"), {"nome": "Wizard Two"})

    client1.post(reverse("accounts:cpf"), {"cpf": "123.456.789-09"})
    client2.post(reverse("accounts:cpf"), {"cpf": "987.654.321-00"})

    client1.post(reverse("accounts:email"), {"email": "wizard1@example.com"})
    client2.post(reverse("accounts:email"), {"email": "wizard2@example.com"})

    client1.post(
        reverse("accounts:senha"),
        {"senha": "Strong123!", "confirmar_senha": "Strong123!"},
    )
    client2.post(
        reverse("accounts:senha"),
        {"senha": "Strong123!", "confirmar_senha": "Strong123!"},
    )

    client1.post(reverse("accounts:foto"))
    client2.post(reverse("accounts:foto"))

    resp1 = client1.post(reverse("accounts:termos"), {"aceitar_termos": "on"})
    assert resp1.status_code == 302

    resp2 = client2.post(reverse("accounts:termos"), {"aceitar_termos": "on"}, follow=True)
    assert resp2.request["PATH_INFO"] == reverse("accounts:usuario")
    messages = [m.message for m in resp2.context["messages"]]
    assert "Nome de usuário já cadastrado." in messages

    assert User.objects.filter(username="wizard").count() == 1
