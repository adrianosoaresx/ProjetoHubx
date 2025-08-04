import pytest
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError


@pytest.mark.parametrize("password", ["abc12345", "abcdefg!", "12345678!", "Abcdefgh"])
def test_invalid_passwords(password):
    with pytest.raises(ValidationError):
        validate_password(password)


def test_valid_password():
    validate_password("Abc12345!")
