from __future__ import annotations

import mimetypes
import shutil
import subprocess
import uuid
from pathlib import Path
from typing import IO
import tempfile

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage



def _upload_media(file: IO[bytes]) -> str | tuple[str, str]:
    """Valida e envia mídia para o storage configurado.

    Retorna o caminho/chave gerado. Para vídeos, retorna também a chave do preview.
    """

    ffmpeg_available = shutil.which("ffmpeg") is not None

    content_type = getattr(file, "content_type", "") or mimetypes.guess_type(file.name)[0] or ""
    size = getattr(file, "size", 0)
    ext = Path(file.name).suffix.lower()

    image_exts = getattr(settings, "FEED_IMAGE_ALLOWED_EXTS", [".jpg", ".jpeg", ".png", ".gif"])
    pdf_exts = getattr(settings, "FEED_PDF_ALLOWED_EXTS", [".pdf"])
    video_exts = getattr(settings, "FEED_VIDEO_ALLOWED_EXTS", [".mp4", ".webm"])

    is_video = False
    if ext in image_exts and content_type.startswith("image/"):
        max_size = getattr(settings, "FEED_IMAGE_MAX_SIZE", 5 * 1024 * 1024)
    elif ext in pdf_exts and content_type == "application/pdf":
        max_size = getattr(settings, "FEED_PDF_MAX_SIZE", 10 * 1024 * 1024)
    elif ext in video_exts and content_type.startswith("video/"):
        max_size = getattr(settings, "FEED_VIDEO_MAX_SIZE", 20 * 1024 * 1024)
        is_video = True
    else:
        raise ValidationError("Formato de arquivo não suportado")

    if is_video and not ffmpeg_available:
        raise ValidationError("O binário 'ffmpeg' é necessário para gerar previews de vídeo")

    if size > max_size:
        raise ValidationError("Arquivo maior que o limite permitido")

    key = f"feed/{uuid.uuid4()}-{file.name}"
    file.seek(0)
    data = file.read()

    preview_key: str | None = None
    if is_video:
        try:
            with tempfile.NamedTemporaryFile(suffix=ext) as src_tmp, tempfile.NamedTemporaryFile(suffix=".jpg") as tmp:
                src_tmp.write(data)
                src_tmp.flush()
                subprocess.run(
                    ["ffmpeg", "-y", "-i", src_tmp.name, "-frames:v", "1", tmp.name],
                    check=True,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                tmp.seek(0)
                preview_key = f"{key}-preview.jpg"
                default_storage.save(preview_key, ContentFile(tmp.read()))
        except Exception:
            preview_key = None

    default_storage.save(key, ContentFile(data))

    return (key, preview_key) if preview_key else key


def upload_media(file: IO[bytes]) -> str | tuple[str, str]:
    """Wrapper que delega o upload para uma task assíncrona."""

    from .tasks import upload_media as upload_media_task

    file.seek(0)
    data = file.read()
    content_type = getattr(file, "content_type", "")

    return upload_media_task.delay(data, file.name, content_type).get()
