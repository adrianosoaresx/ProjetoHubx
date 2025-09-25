import pytest
from django.contrib.auth import get_user_model

from accounts.models import UserType

pytestmark = pytest.mark.django_db


def test_user_type_enum_contains_operador_and_consultor():
    assert UserType.OPERADOR.value == "operador"
    assert UserType.CONSULTOR.value == "consultor"


def test_get_tipo_usuario_returns_explicit_value_for_new_roles():
    user_model = get_user_model()
    user = user_model.objects.create_user(
        email="operador@example.com",
        username="operador",
        password="s3cret",
        user_type=UserType.OPERADOR,
    )

    assert user.get_tipo_usuario == UserType.OPERADOR.value
