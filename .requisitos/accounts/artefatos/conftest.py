import pytest
from accounts.models import User
from django.contrib.auth.hashers import make_password

@pytest.fixture
def user_factory(db):
    def create_user(**kwargs):
        data = {
            "username": "usuario",
            "email": "teste@example.com",
            "nome_completo": "Usuário Teste",
            "cpf": "00000000000",
            "password": make_password("Senha123!"),
            "is_associado": True,
        }
        data.update(kwargs)
        return User.objects.create(**data)
    return create_user
