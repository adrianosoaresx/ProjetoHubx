import pytest

from accounts.forms import CustomUserCreationForm


@pytest.mark.django_db
def test_creation_requires_identifier():
    form = CustomUserCreationForm(
        data={
            "email": "blank@example.com",
            "cpf": "",
            "cnpj": "",
            "password1": "StrongPass1!",
            "password2": "StrongPass1!",
        }
    )
    assert not form.is_valid()
    assert "cpf" in form.errors


@pytest.mark.django_db
def test_clean_cpf_accepts_formatted_cpf():
    form = CustomUserCreationForm(
        data={
            "email": "formatted@example.com",
            "cpf": "123.456.789-09",
            "cnpj": "",
            "password1": "StrongPass1!",
            "password2": "StrongPass1!",
        }
    )
    assert form.is_valid(), form.errors
    assert form.cleaned_data.get("cpf") == "123.456.789-09"


@pytest.mark.django_db
def test_clean_cpf_rejects_invalid_cpf():
    form = CustomUserCreationForm(
        data={
            "email": "invalid@example.com",
            "cpf": "123.456.789-00",
            "cnpj": "",
            "password1": "StrongPass1!",
            "password2": "StrongPass1!",
        }
    )
    assert not form.is_valid()
    assert "cpf" in form.errors
