from __future__ import annotations

import mimetypes
import uuid
from typing import IO

import boto3
from botocore.exceptions import ClientError
from django.conf import settings
from django.core.exceptions import ValidationError


def upload_media(file: IO[bytes]) -> str:
    """Upload media to S3 with simple retry logic.

    Returns the generated presigned URL.
    """
    content_type = getattr(file, "content_type", None) or mimetypes.guess_type(file.name)[0]
    size = getattr(file, "size", 0)
    ext = (file.name or "").lower()

    limits = {
        "image": 5 * 1024 * 1024,
        "video": 20 * 1024 * 1024,
        "pdf": 10 * 1024 * 1024,
    }
    kind = "image"
    if content_type:
        if content_type.startswith("video/"):
            kind = "video"
        elif content_type == "application/pdf" or ext.endswith(".pdf"):
            kind = "pdf"
    if size > limits[kind]:
        raise ValidationError("Arquivo maior que o permitido")

    bucket = getattr(settings, "AWS_STORAGE_BUCKET_NAME", "")
    key = f"feed/{uuid.uuid4()}-{file.name}"
    if bucket:
        client = boto3.client("s3")
        for attempt in range(3):
            try:
                file.seek(0)
                client.upload_fileobj(file, bucket, key)
                break
            except ClientError:
                if attempt == 2:
                    raise
        return client.generate_presigned_url("get_object", Params={"Bucket": bucket, "Key": key}, ExpiresIn=3600)
    # Sem S3 configurado, retorna caminho gerado
    return key
