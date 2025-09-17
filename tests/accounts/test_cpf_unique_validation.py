import pytest
from django.contrib.auth import get_user_model

from accounts.forms import InformacoesPessoaisForm

User = get_user_model()


@pytest.mark.django_db
def test_cpf_duplicate_validation():
    User.objects.create_user(email="a@example.com", username="a", cpf="390.533.447-05")
    user = User.objects.create_user(email="b@example.com", username="b", cpf="529.982.247-25")
    form = InformacoesPessoaisForm(
        data={
            "first_name": "Teste",
            "username": "b",
            "email": "b@example.com",
            "cpf": "390.533.447-05",
        },
        instance=user,
    )
    assert not form.is_valid()
    assert "cpf" in form.errors


@pytest.mark.django_db
def test_cnpj_duplicate_validation():
    User.objects.create_user(email="c@example.com", username="c", cnpj="00.000.000/0001-91")
    user = User.objects.create_user(email="d@example.com", username="d", cnpj="00.000.000/0002-72")
    form = InformacoesPessoaisForm(
        data={
            "first_name": "Teste",
            "username": "d",
            "email": "d@example.com",
            "cpf": "",
            "cnpj": "00.000.000/0001-91",
        },
        instance=user,
    )
    assert not form.is_valid()
    assert "cnpj" in form.errors
