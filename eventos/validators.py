import mimetypes
import os

from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _


SAFE_MIME_TYPES = {
    "image/jpeg": {".jpg", ".jpeg"},
    "image/png": {".png"},
    "application/pdf": {".pdf"},
}


def validate_uploaded_file(f):
    """Valida tipo, extensão e tamanho de arquivos de upload."""

    ext = os.path.splitext(f.name)[1].lower()
    content_type = getattr(f, "content_type", "") or mimetypes.guess_type(f.name)[0] or ""
    allowed_exts = SAFE_MIME_TYPES.get(content_type)
    if not allowed_exts:
        raise ValidationError(_("Tipo de arquivo não permitido."))
    if ext not in allowed_exts:
        raise ValidationError(_("Extensão do arquivo não corresponde ao tipo MIME."))
    if content_type == "application/pdf":
        max_size = 20 * 1024 * 1024
    else:
        max_size = 10 * 1024 * 1024
    if f.size > max_size:
        raise ValidationError(_("Arquivo excede o tamanho máximo permitido."))

