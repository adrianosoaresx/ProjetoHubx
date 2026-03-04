import mimetypes
from pathlib import Path

from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

from core.uploads.validators import validate_upload


def validate_uploaded_file(f):
    """Valida uploads de eventos (imagem ou PDF)."""
    content_type = getattr(f, "content_type", "") or mimetypes.guess_type(f.name)[0] or ""
    ext = Path(f.name).suffix.lower()

    image_exts = set(getattr(settings, "UPLOAD_ALLOWED_IMAGE_EXTS", [".jpg", ".jpeg", ".png", ".gif", ".webp"]))
    pdf_exts = set(getattr(settings, "UPLOAD_ALLOWED_PDF_EXTS", [".pdf"]))

    if content_type.startswith("image/") or ext in image_exts:
        category = "image"
    elif content_type == "application/pdf" or ext in pdf_exts:
        category = "pdf"
    else:
        raise ValidationError(_("Tipo de arquivo não permitido."))

    validate_upload(f, category)
