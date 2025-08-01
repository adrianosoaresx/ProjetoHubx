import pytest
from django.contrib.auth import get_user_model

from accounts.forms import InformacoesPessoaisForm

User = get_user_model()


@pytest.mark.django_db
def test_cpf_duplicate_validation():
    User.objects.create_user(email="a@example.com", username="a", cpf="123.456.789-00")
    user = User.objects.create_user(email="b@example.com", username="b", cpf="321.654.987-00")
    form = InformacoesPessoaisForm(
        data={
            "nome_completo": "Teste",
            "username": "b",
            "email": "b@example.com",
            "cpf": "123.456.789-00",
        },
        instance=user,
    )
    assert not form.is_valid()
    assert "cpf" in form.errors
