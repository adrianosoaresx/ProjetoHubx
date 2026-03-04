import mimetypes
from pathlib import Path

from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _


def validate_upload(file, category):
    """Valida extensão, MIME e tamanho de arquivo de acordo com a categoria."""
    if not file:
        return

    defaults = {
        "image": {
            "allowed_exts": [".jpg", ".jpeg", ".png", ".gif", ".webp"],
            "settings_exts": "UPLOAD_ALLOWED_IMAGE_EXTS",
            "max_size": 10 * 1024 * 1024,
            "settings_max": "UPLOAD_MAX_IMAGE_SIZE",
            "mime": lambda ct: ct.startswith("image/"),
        },
        "video": {
            "allowed_exts": [".mp4", ".webm"],
            "settings_exts": "UPLOAD_ALLOWED_VIDEO_EXTS",
            "max_size": 50 * 1024 * 1024,
            "settings_max": "UPLOAD_MAX_VIDEO_SIZE",
            "mime": lambda ct: ct.startswith("video/"),
        },
        "pdf": {
            "allowed_exts": [".pdf"],
            "settings_exts": "UPLOAD_ALLOWED_PDF_EXTS",
            "max_size": 50 * 1024 * 1024,
            "settings_max": "UPLOAD_MAX_PDF_SIZE",
            "mime": lambda ct: ct == "application/pdf",
        },
    }

    if category not in defaults:
        raise ValidationError(_("Categoria de upload inválida."))

    config = defaults[category]
    allowed_exts = set(getattr(settings, config["settings_exts"], config["allowed_exts"]))
    max_size = getattr(settings, config["settings_max"], config["max_size"])

    ext = Path(file.name).suffix.lower()
    content_type = getattr(file, "content_type", "") or mimetypes.guess_type(file.name)[0] or ""

    if ext not in allowed_exts:
        raise ValidationError(_("Formato de arquivo não permitido."))

    if not config["mime"](content_type):
        raise ValidationError(_("Tipo de arquivo não permitido."))

    if file.size > max_size:
        raise ValidationError(_("Arquivo excede o tamanho máximo permitido."))
