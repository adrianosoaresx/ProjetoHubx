import mimetypes
import os

from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _


def validate_uploaded_file(f):
    """Valida tipo, extensão e tamanho de arquivos de upload."""

    ext = os.path.splitext(f.name)[1].lower()
    content_type = getattr(f, "content_type", "") or mimetypes.guess_type(f.name)[0] or ""

    image_exts = set(getattr(settings, "UPLOAD_ALLOWED_IMAGE_EXTS", [".jpg", ".jpeg", ".png", ".gif", ".webp"]))
    pdf_exts = set(getattr(settings, "UPLOAD_ALLOWED_PDF_EXTS", [".pdf"]))

    if content_type.startswith("image/"):
        allowed_exts = image_exts
        max_size = getattr(settings, "UPLOAD_MAX_IMAGE_SIZE", 10 * 1024 * 1024)
    elif content_type == "application/pdf":
        allowed_exts = pdf_exts
        max_size = getattr(settings, "UPLOAD_MAX_PDF_SIZE", 100 * 1024 * 1024)
    else:
        raise ValidationError(_("Tipo de arquivo não permitido."))

    if ext not in allowed_exts:
        raise ValidationError(_("Extensão do arquivo não corresponde ao tipo MIME."))
    if f.size > max_size:
        raise ValidationError(_("Arquivo excede o tamanho máximo permitido."))
