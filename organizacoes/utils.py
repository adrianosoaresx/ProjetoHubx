import re

from django.core.exceptions import ValidationError
from validate_docbr import CNPJ

from core.uploads.validators import validate_upload

cnpj_validator = CNPJ()


def validate_cnpj(value: str) -> str:
    """Validate a CNPJ and return its masked form."""
    digits = re.sub(r"\D", "", value or "")
    if not cnpj_validator.validate(digits):
        raise ValidationError("CNPJ inválido.")
    return cnpj_validator.mask(digits)


def validate_organizacao_image(file) -> None:
    validate_upload(file, "image")
