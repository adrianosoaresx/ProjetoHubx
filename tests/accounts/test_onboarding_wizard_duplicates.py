import pytest
from django.contrib.messages import get_messages
from django.urls import reverse

from django.contrib.auth import get_user_model


User = get_user_model()


@pytest.mark.django_db
def test_cpf_step_rejects_duplicate(client):
    User.objects.create_user(email="a@example.com", username="a", cpf="123.456.789-09")
    resp = client.post(reverse("accounts:cpf"), {"cpf": "123.456.789-09"})
    assert resp.status_code == 302
    messages = list(get_messages(resp.wsgi_request))
    assert any("CPF já cadastrado." in m.message for m in messages)


@pytest.mark.django_db
def test_email_step_rejects_duplicate(client):
    User.objects.create_user(email="dup@example.com", username="dup")
    resp = client.post(reverse("accounts:email"), {"email": "dup@example.com"})
    assert resp.status_code == 302
    messages = list(get_messages(resp.wsgi_request))
    assert any("e-mail já está em uso" in m.message.lower() for m in messages)


@pytest.mark.django_db
def test_usuario_step_rejects_duplicate(client):
    User.objects.create_user(email="u@example.com", username="existente")
    resp = client.post(reverse("accounts:usuario"), {"usuario": "existente"})
    assert resp.status_code == 302
    messages = list(get_messages(resp.wsgi_request))
    assert any("nome de usuário já cadastrado" in m.message.lower() for m in messages)
