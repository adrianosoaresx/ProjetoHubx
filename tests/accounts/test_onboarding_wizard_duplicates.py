import pytest
from django.contrib.auth import get_user_model
from django.contrib.messages import get_messages
from django.urls import reverse


User = get_user_model()


@pytest.mark.django_db
def test_cpf_step_requires_identifier(client):
    resp = client.post(reverse("accounts:cpf"), {"cpf": "", "cnpj": ""})
    assert resp.status_code == 302
    messages = list(get_messages(resp.wsgi_request))
    assert any("Informe CPF ou CNPJ." in m.message for m in messages)


@pytest.mark.django_db
def test_cpf_step_rejects_duplicate_when_existing_without_cnpj(client):
    User.objects.create_user(email="a@example.com", username="a", cpf="123.456.789-09")
    resp = client.post(reverse("accounts:cpf"), {"cpf": "123.456.789-09"})
    assert resp.status_code == 302
    messages = list(get_messages(resp.wsgi_request))
    assert any("Para reutilizar este CPF" in m.message for m in messages)


@pytest.mark.django_db
def test_cpf_step_allows_duplicate_with_cnpj(client):
    User.objects.create_user(
        email="b@example.com",
        username="b",
        cpf="390.533.447-05",
        cnpj="00.000.000/0001-91",
    )
    resp = client.post(
        reverse("accounts:cpf"),
        {"cpf": "390.533.447-05", "cnpj": "00.000.000/0002-72"},
    )
    assert resp.status_code == 302
    assert resp.url == reverse("accounts:email")
    session = client.session
    assert session["cpf"] == "390.533.447-05"
    assert session["cnpj"] == "00.000.000/0002-72"


@pytest.mark.django_db
def test_cpf_step_accepts_only_cnpj(client):
    resp = client.post(reverse("accounts:cpf"), {"cpf": "", "cnpj": "00.000.000/0003-53"})
    assert resp.status_code == 302
    assert resp.url == reverse("accounts:email")
    session = client.session
    assert "cpf" not in session or not session["cpf"]
    assert session["cnpj"] == "00.000.000/0003-53"


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
