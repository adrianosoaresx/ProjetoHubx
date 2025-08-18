from __future__ import annotations

from unittest.mock import Mock

import pytest
from botocore.exceptions import ClientError
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile

from feed.services import upload_media


@pytest.mark.django_db
def test_upload_media_capture_exception(monkeypatch, settings):
    settings.AWS_STORAGE_BUCKET_NAME = "bucket"
    settings.CELERY_TASK_EAGER_PROPAGATES = False
    file = SimpleUploadedFile("a.png", b"data", content_type="image/png")

    def fail(*args, **kwargs):
        raise ClientError({"Error": {}}, "upload")

    monkeypatch.setattr("feed.services._upload_media", fail)
    captured = Mock()
    monkeypatch.setattr("feed.tasks.capture_exception", captured)

    with pytest.raises(ClientError):
        upload_media(file)

    assert captured.call_count == 4


@pytest.mark.django_db
def test_upload_media_retries(monkeypatch, settings):
    settings.AWS_STORAGE_BUCKET_NAME = "bucket"
    settings.CELERY_TASK_EAGER_PROPAGATES = False
    file = SimpleUploadedFile("a.png", b"data", content_type="image/png")
    calls = {"n": 0}

    def flaky(*args, **kwargs):
        calls["n"] += 1
        if calls["n"] < 3:
            raise ClientError({"Error": {}}, "upload")
        return "ok"

    monkeypatch.setattr("feed.services._upload_media", flaky)
    url = upload_media(file)
    assert url == "ok"
    assert calls["n"] == 3


@pytest.mark.django_db
def test_upload_media_invalid_size(settings):
    settings.AWS_STORAGE_BUCKET_NAME = "bucket"
    big = SimpleUploadedFile(
        "a.pdf",
        b"x" * (10 * 1024 * 1024 + 1),
        content_type="application/pdf",
    )
    with pytest.raises(ValidationError):
        upload_media(big)
