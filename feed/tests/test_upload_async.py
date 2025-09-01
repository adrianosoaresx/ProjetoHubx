from __future__ import annotations

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from unittest.mock import Mock, patch

from accounts.factories import UserFactory
from organizacoes.factories import OrganizacaoFactory
from feed.models import PendingUpload, Post
from feed.services import upload_media
from feed.tasks import finalize_upload


class UploadAsyncTest(TestCase):
    @override_settings(CELERY_TASK_ALWAYS_EAGER=False)
    @patch("feed.tasks.upload_media.apply_async")
    def test_pending_upload_updates_post(self, mock_apply):
        mock_apply.return_value = Mock(id="task123")
        file = SimpleUploadedFile("a.png", b"data", content_type="image/png")
        identifier = upload_media(file)
        assert identifier.startswith("pending:")
        pending_id = identifier.split(":", 1)[1]
        assert PendingUpload.objects.filter(id=pending_id, task_id="task123").exists()

        org = OrganizacaoFactory()
        user = UserFactory(organizacao=org)
        post = Post.objects.create(
            autor=user,
            organizacao=user.organizacao,
            tipo_feed="global",
            image=identifier,
        )
        finalize_upload("real-key", pending_id)
        post.refresh_from_db()
        assert post.image == "real-key"
        assert not PendingUpload.objects.filter(id=pending_id).exists()

    @override_settings(CELERY_TASK_ALWAYS_EAGER=False)
    @patch("feed.tasks.upload_media.apply_async")
    def test_pending_video_updates_preview(self, mock_apply):
        mock_apply.return_value = Mock(id="task456")
        file = SimpleUploadedFile("v.mp4", b"00", content_type="video/mp4")
        identifier = upload_media(file)
        pending_id = identifier.split(":", 1)[1]
        org = OrganizacaoFactory()
        user = UserFactory(organizacao=org)
        post = Post.objects.create(
            autor=user,
            organizacao=user.organizacao,
            tipo_feed="global",
            video=identifier,
        )
        finalize_upload(("vid-key", "prev-key"), pending_id)
        post.refresh_from_db()
        assert post.video == "vid-key"
        assert post.video_preview == "prev-key"
        assert not PendingUpload.objects.filter(id=pending_id).exists()
