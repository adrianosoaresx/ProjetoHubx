from __future__ import annotations

import mimetypes
from pathlib import Path

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import UploadedFile
from django.utils.translation import gettext_lazy as _

try:  # pragma: no cover - dependência opcional
    import magic  # type: ignore
except Exception:  # pragma: no cover - fallback
    magic = None


def _get_mime(file: UploadedFile) -> str | None:
    if magic:
        mime = magic.from_buffer(file.read(2048), mime=True)
        file.seek(0)
        return str(mime)
    return mimetypes.guess_type(file.name)[0]


def validate_attachment(file: UploadedFile) -> None:
    """Valida anexos de resposta conforme configuração."""
    max_bytes = settings.DISCUSSAO_MAX_FILE_MB * 1024 * 1024
    if file.size > max_bytes:
        raise ValidationError(
            _("Arquivo excede o tamanho máximo de %(max)d MB."),
            params={"max": settings.DISCUSSAO_MAX_FILE_MB},
        )
    ext = Path(file.name).suffix.lower()
    if ext not in settings.DISCUSSAO_ALLOWED_EXTS:
        raise ValidationError(_("Tipo de arquivo não permitido."))
    mime_type = _get_mime(file)
    if mime_type and not any(
        mime_type.startswith(prefix) for prefix in settings.DISCUSSAO_ALLOWED_MIME_PREFIXES
    ):
        raise ValidationError(_("Tipo de arquivo não permitido."))
