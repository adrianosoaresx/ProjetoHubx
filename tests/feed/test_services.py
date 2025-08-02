from __future__ import annotations

from unittest.mock import Mock

import boto3
import pytest
from botocore.exceptions import ClientError
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile

from feed.services import upload_media


@pytest.mark.django_db
def test_upload_media_retries(monkeypatch, settings):
    settings.AWS_STORAGE_BUCKET_NAME = "bucket"
    file = SimpleUploadedFile("a.png", b"data", content_type="image/png")
    client = Mock()
    calls = {"n": 0}

    def upload_fileobj(f, bucket, key):
        calls["n"] += 1
        if calls["n"] < 3:
            raise ClientError({"Error": {}}, "upload")

    client.upload_fileobj = upload_fileobj
    client.generate_presigned_url = lambda *a, **k: f"url/{k['Params']['Key']}"
    monkeypatch.setattr(boto3, "client", lambda *a, **k: client)
    url = upload_media(file)
    assert url.startswith("url/")
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
