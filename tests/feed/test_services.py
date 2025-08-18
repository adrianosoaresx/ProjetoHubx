from __future__ import annotations

import subprocess
import tempfile

import pytest
from django.core.exceptions import ValidationError
from django.core.files.storage import default_storage
from django.core.files.uploadedfile import SimpleUploadedFile

from feed.services import upload_media


def _make_video_file() -> SimpleUploadedFile:
    tmp = tempfile.NamedTemporaryFile(suffix=".mp4")
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-f",
            "lavfi",
            "-i",
            "color=c=black:s=16x16:d=1",
            "-pix_fmt",
            "yuv420p",
            tmp.name,
        ],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    tmp.seek(0)
    return SimpleUploadedFile("v.mp4", tmp.read(), content_type="video/mp4")


@pytest.mark.django_db
def test_upload_media_generates_preview():
    video = _make_video_file()
    video_key, preview_key = upload_media(video)
    assert preview_key
    assert default_storage.exists(video_key)
    assert default_storage.exists(preview_key)


@pytest.mark.django_db
def test_upload_media_invalid_size():
    big = SimpleUploadedFile(
        "a.pdf",
        b"x" * (10 * 1024 * 1024 + 1),
        content_type="application/pdf",
    )
    with pytest.raises(ValidationError):
        upload_media(big)
