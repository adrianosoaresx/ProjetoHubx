from pathlib import Path

import pytest
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile

from accounts.models import UserMedia

User = get_user_model()


@pytest.mark.django_db
def test_user_media_delete_removes_file(tmp_path, settings):
    settings.MEDIA_ROOT = tmp_path
    user = User.objects.create_user(email="u@example.com", username="u", password="pass")
    uploaded = SimpleUploadedFile("doc.txt", b"hello", content_type="text/plain")
    media = UserMedia.objects.create(user=user, file=uploaded)

    file_path = Path(media.file.path)
    assert file_path.exists()

    media.delete(soft=False)

    assert not file_path.exists()
    assert not UserMedia.all_objects.filter(pk=media.pk).exists()
