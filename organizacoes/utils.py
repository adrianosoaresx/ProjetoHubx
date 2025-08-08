import re
from django.core.exceptions import ValidationError
from validate_docbr import CNPJ

cnpj_validator = CNPJ()


def validate_cnpj(value: str) -> str:
    """Validate a CNPJ and return its masked form."""
    digits = re.sub(r"\D", "", value or "")
    if not cnpj_validator.validate(digits):
        raise ValidationError("CNPJ inválido.")
    return cnpj_validator.mask(digits)
