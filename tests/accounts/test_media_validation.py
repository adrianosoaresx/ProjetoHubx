import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile

from accounts.models import UserMedia

User = get_user_model()


@pytest.mark.django_db
def test_user_media_invalid_extension(tmp_path, settings):
    settings.MEDIA_ROOT = tmp_path
    user = User.objects.create_user(email="u@example.com", username="u", password="pass")
    f = SimpleUploadedFile("malware.exe", b"x", content_type="application/octet-stream")
    media = UserMedia(user=user, file=f)
    with pytest.raises(ValidationError):
        media.clean()


@pytest.mark.django_db
def test_user_media_size_limit(tmp_path, settings):
    settings.MEDIA_ROOT = tmp_path
    settings.USER_MEDIA_MAX_SIZE = 1
    user = User.objects.create_user(email="u2@example.com", username="u2", password="pass")
    f = SimpleUploadedFile("video.mp4", b"xx", content_type="video/mp4")
    media = UserMedia(user=user, file=f)
    with pytest.raises(ValidationError):
        media.clean()
