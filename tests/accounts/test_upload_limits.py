from django.conf import settings


def test_user_media_size_not_capped_by_request_limits():
    assert settings.DATA_UPLOAD_MAX_MEMORY_SIZE >= settings.USER_MEDIA_MAX_SIZE
    assert settings.FILE_UPLOAD_MAX_MEMORY_SIZE == settings.DATA_UPLOAD_MAX_MEMORY_SIZE
