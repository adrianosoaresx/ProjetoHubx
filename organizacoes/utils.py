import os
import re

from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from validate_docbr import CNPJ

cnpj_validator = CNPJ()


def validate_cnpj(value: str) -> str:
    """Validate a CNPJ and return its masked form."""
    digits = re.sub(r"\D", "", value or "")
    if not cnpj_validator.validate(digits):
        raise ValidationError("CNPJ inválido.")
    return cnpj_validator.mask(digits)


def validate_organizacao_image(file) -> None:
    if not file:
        return
    allowed_exts = {f".{ext.lower()}" for ext in settings.ORGANIZACOES_ALLOWED_IMAGE_EXTENSIONS}
    max_size = settings.ORGANIZACOES_MAX_IMAGE_SIZE
    ext = os.path.splitext(file.name)[1].lower()
    if ext not in allowed_exts:
        raise ValidationError(_("Formato de imagem não suportado."))
    if file.size > max_size:
        raise ValidationError(_("Imagem excede o tamanho máximo permitido."))
