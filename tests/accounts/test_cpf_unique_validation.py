import pytest
from django.contrib.auth import get_user_model

from accounts.forms import InformacoesPessoaisForm

User = get_user_model()


@pytest.mark.django_db
def test_personal_info_requires_identifier():
    user = User.objects.create_user(email="user@example.com", username="user", cpf="529.982.247-25")
    form = InformacoesPessoaisForm(
        data={
            "contato": "Teste",
            "username": "user",
            "email": "user@example.com",
            "cpf": "",
            "cnpj": "",
        },
        instance=user,
    )
    assert not form.is_valid()
    assert "cpf" in form.errors


@pytest.mark.django_db
def test_personal_info_allows_duplicate_cpf_when_all_have_cnpj():
    User.objects.create_user(
        email="a@example.com",
        username="a",
        cpf="390.533.447-05",
        cnpj="00.000.000/0001-91",
    )
    user = User.objects.create_user(email="b@example.com", username="b")
    form = InformacoesPessoaisForm(
        data={
            "contato": "Teste",
            "username": "b",
            "email": "b@example.com",
            "cpf": "390.533.447-05",
            "cnpj": "00.000.000/0002-72",
        },
        instance=user,
    )
    assert form.is_valid(), form.errors


@pytest.mark.django_db
def test_personal_info_blocks_duplicate_cpf_when_existing_missing_cnpj():
    User.objects.create_user(email="c@example.com", username="c", cpf="529.982.247-25")
    user = User.objects.create_user(email="d@example.com", username="d")
    form = InformacoesPessoaisForm(
        data={
            "contato": "Teste",
            "username": "d",
            "email": "d@example.com",
            "cpf": "529.982.247-25",
            "cnpj": "00.000.000/0003-53",
        },
        instance=user,
    )
    assert not form.is_valid()
    assert "cpf" in form.errors


@pytest.mark.django_db
def test_personal_info_rejects_duplicate_cnpj():
    User.objects.create_user(email="e@example.com", username="e", cnpj="00.000.000/0004-34")
    user = User.objects.create_user(email="f@example.com", username="f")
    form = InformacoesPessoaisForm(
        data={
            "contato": "Teste",
            "username": "f",
            "email": "f@example.com",
            "cpf": "",
            "cnpj": "00.000.000/0004-34",
        },
        instance=user,
    )
    assert not form.is_valid()
    assert "cnpj" in form.errors
