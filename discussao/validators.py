from __future__ import annotations

import mimetypes
from pathlib import Path

from django.conf import settings
from django.core.exceptions import ValidationError


def validar_arquivo_discussao(arquivo) -> None:
    """Valida arquivos enviados nas respostas das discussões.

    Aceita apenas imagens e PDFs dentro do limite de tamanho configurado.
    """
    if not arquivo:
        return
    content_type = getattr(arquivo, "content_type", "") or mimetypes.guess_type(arquivo.name)[0] or ""
    size = getattr(arquivo, "size", 0)
    ext = Path(arquivo.name).suffix.lower()

    image_exts = getattr(settings, "FEED_IMAGE_ALLOWED_EXTS", [".jpg", ".jpeg", ".png", ".gif"])
    pdf_exts = getattr(settings, "FEED_PDF_ALLOWED_EXTS", [".pdf"])

    if ext in image_exts and content_type.startswith("image/"):
        max_size = getattr(settings, "FEED_IMAGE_MAX_SIZE", 5 * 1024 * 1024)
    elif ext in pdf_exts and content_type == "application/pdf":
        max_size = getattr(settings, "FEED_PDF_MAX_SIZE", 10 * 1024 * 1024)
    else:
        raise ValidationError("Formato de arquivo não suportado")

    if size > max_size:
        raise ValidationError("Arquivo maior que o limite permitido")
