from __future__ import annotations

import mimetypes
from pathlib import Path

import clamd
from django.conf import settings
from django.core.exceptions import ValidationError


def validar_arquivo_discussao(arquivo) -> None:
    """Valida arquivos enviados nas respostas das discussões.

    Aceita apenas imagens e PDFs dentro dos limites configurados em
    ``DISCUSSAO_IMAGE_MAX_SIZE`` e ``DISCUSSAO_PDF_MAX_SIZE``.
    """
    if not arquivo:
        return
    content_type = getattr(arquivo, "content_type", "") or mimetypes.guess_type(arquivo.name)[0] or ""
    size = getattr(arquivo, "size", 0)
    ext = Path(arquivo.name).suffix.lower()

    image_exts = getattr(settings, "DISCUSSAO_IMAGE_ALLOWED_EXTS", [".jpg", ".jpeg", ".png", ".gif"])
    pdf_exts = getattr(settings, "DISCUSSAO_PDF_ALLOWED_EXTS", [".pdf"])

    if ext in image_exts and content_type.startswith("image/"):
        max_size = getattr(settings, "DISCUSSAO_IMAGE_MAX_SIZE", 5 * 1024 * 1024)
    elif ext in pdf_exts and content_type == "application/pdf":
        max_size = getattr(settings, "DISCUSSAO_PDF_MAX_SIZE", 10 * 1024 * 1024)
    else:
        raise ValidationError("Formato de arquivo não suportado")

    if size > max_size:
        raise ValidationError("Arquivo maior que o limite permitido")

    # Scan the uploaded content using ClamAV. If any issue is found, reject
    # the file to avoid potentially malicious uploads.
    status = "ERROR"
    try:
        scanner = clamd.ClamdUnixSocket()
        result = scanner.scan_stream(arquivo.read())
        status = result.get("stream", (None,))[0]
    except Exception:
        # In case of any failure during scanning, be conservative and mark
        # as a potential threat.
        status = "ERROR"
    finally:
        # Restore file pointer for further processing
        try:
            arquivo.seek(0)
        except Exception:
            pass

    if status != "OK":
        raise ValidationError("Arquivo potencialmente malicioso")
