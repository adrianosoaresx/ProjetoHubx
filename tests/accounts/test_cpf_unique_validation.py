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
            "nome_completo": "Teste",
            "username": "b",
            "email": "b@example.com",
            "cpf": "390.533.447-05",
        },
        instance=user,
    )
    assert not form.is_valid()
    assert "cpf" in form.errors
