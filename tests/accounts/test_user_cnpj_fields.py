import pytest

from django.contrib.auth import get_user_model

from accounts.forms import CustomUserCreationForm, InformacoesPessoaisForm

User = get_user_model()


@pytest.mark.django_db
def test_custom_user_creation_form_saves_cnpj_razao_social_and_nome_fantasia():
    form = CustomUserCreationForm(
        data={
            "email": "empresa@example.com",
            "cpf": "",
            "cnpj": "00000000000191",
            "razao_social": "Empresa Teste LTDA",
            "nome_fantasia": "Empresa Teste",
            "password1": "StrongPass1!",
            "password2": "StrongPass1!",
        }
    )

    assert form.is_valid(), form.errors

    user = form.save()
    user.refresh_from_db()

    assert user.cnpj == "00.000.000/0001-91"
    assert user.razao_social == "Empresa Teste LTDA"
    assert user.nome_fantasia == "Empresa Teste"


@pytest.mark.django_db
def test_informacoes_pessoais_form_updates_cnpj_razao_social_and_nome_fantasia():
    user = User.objects.create_user(
        email="user@example.com",
        username="user",
        password="StrongPass1!",
        first_name="Old",
        last_name="Name",
        cnpj="00.000.000/0001-91",
        razao_social="Empresa Antiga",
        nome_fantasia="Empresa Antiga",
    )

    form = InformacoesPessoaisForm(
        data={
            "first_name": "Novo",
            "last_name": "Nome",
            "username": user.username,
            "email": user.email,
            "cpf": "",
            "cnpj": "00000000000272",
            "razao_social": "Empresa Nova LTDA",
            "nome_fantasia": "Empresa Nova",
        },
        instance=user,
    )

    assert form.is_valid(), form.errors

    form.save()
    user.refresh_from_db()

    assert user.cnpj == "00.000.000/0002-72"
    assert user.razao_social == "Empresa Nova LTDA"
    assert user.nome_fantasia == "Empresa Nova"
