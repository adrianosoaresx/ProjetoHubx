from __future__ import annotations

import mimetypes
import uuid
from pathlib import Path
from typing import IO

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.files.storage import default_storage


def upload_media(file: IO[bytes]) -> str:
    """Valida e envia mídia para o storage configurado.

    Retorna apenas o caminho/chave gerado, sem URL assinada.
    """

    content_type = getattr(file, "content_type", "") or mimetypes.guess_type(file.name)[0] or ""
    size = getattr(file, "size", 0)
    ext = Path(file.name).suffix.lower()

    image_exts = getattr(settings, "FEED_IMAGE_ALLOWED_EXTS", [".jpg", ".jpeg", ".png", ".gif"])
    pdf_exts = getattr(settings, "FEED_PDF_ALLOWED_EXTS", [".pdf"])
    video_exts = getattr(settings, "FEED_VIDEO_ALLOWED_EXTS", [".mp4", ".webm"])

    if ext in image_exts and content_type.startswith("image/"):
        max_size = getattr(settings, "FEED_IMAGE_MAX_SIZE", 5 * 1024 * 1024)
    elif ext in pdf_exts and content_type == "application/pdf":
        max_size = getattr(settings, "FEED_PDF_MAX_SIZE", 10 * 1024 * 1024)
    elif ext in video_exts and content_type.startswith("video/"):
        max_size = getattr(settings, "FEED_VIDEO_MAX_SIZE", 20 * 1024 * 1024)
    else:
        raise ValidationError("Formato de arquivo não suportado")

    if size > max_size:
        raise ValidationError("Arquivo maior que o limite permitido")

    key = f"feed/{uuid.uuid4()}-{file.name}"
    file.seek(0)
    default_storage.save(key, file)
    return key
