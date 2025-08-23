import pytest
from django.contrib.messages import get_messages
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse


@pytest.mark.django_db
def test_foto_invalid_extension(client, settings, tmp_path):
    settings.ROOT_URLCONF = "tests.urls_accounts"
    settings.MEDIA_ROOT = tmp_path
    settings.USER_MEDIA_ALLOWED_EXTS = [".jpg"]
    f = SimpleUploadedFile("malware.exe", b"x", content_type="application/octet-stream")
    resp = client.post(reverse("accounts:foto"), {"foto": f})
    assert resp.status_code == 302
    messages = list(get_messages(resp.wsgi_request))
    assert any("Formato de arquivo não permitido" in m.message for m in messages)
    assert "foto" not in client.session


@pytest.mark.django_db
def test_foto_size_limit(client, settings, tmp_path):
    settings.ROOT_URLCONF = "tests.urls_accounts"
    settings.MEDIA_ROOT = tmp_path
    settings.USER_MEDIA_ALLOWED_EXTS = [".jpg"]
    settings.USER_MEDIA_MAX_SIZE = 1
    f = SimpleUploadedFile("big.jpg", b"xx", content_type="image/jpeg")
    resp = client.post(reverse("accounts:foto"), {"foto": f})
    assert resp.status_code == 302
    messages = list(get_messages(resp.wsgi_request))
    assert any("Arquivo excede o tamanho máximo permitido" in m.message for m in messages)
    assert "foto" not in client.session
