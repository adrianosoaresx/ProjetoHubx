from pathlib import Path

import pytest
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile

User = get_user_model()

IMAGE = (
    b"\x47\x49\x46\x38\x39\x61\x01\x00\x01\x00\x80\x00\x00\x00\x00\x00"
    b"\xff\xff\xff!\xf9\x04\x01\x0a\x00\x01\x00,\x00\x00\x00\x00\x01\x00"
    b"\x01\x00\x00\x02\x02L\x01\x00;"
)


@pytest.mark.django_db
def test_user_delete_removes_avatar_and_cover(tmp_path, settings):
    settings.MEDIA_ROOT = tmp_path
    avatar = SimpleUploadedFile("avatar.gif", IMAGE, content_type="image/gif")
    cover = SimpleUploadedFile("cover.gif", IMAGE, content_type="image/gif")
    user = User.objects.create_user(
        email="u@example.com",
        username="u",
        password="pass",
        avatar=avatar,
        cover=cover,
    )

    avatar_path = Path(user.avatar.path)
    cover_path = Path(user.cover.path)
    assert avatar_path.exists()
    assert cover_path.exists()

    user.delete(soft=False)

    assert not avatar_path.exists()
    assert not cover_path.exists()
    assert not User.all_objects.filter(pk=user.pk).exists()
