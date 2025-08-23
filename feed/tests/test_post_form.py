from __future__ import annotations

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from PIL import Image
import io
from unittest.mock import patch
from django.urls import reverse

from accounts.factories import UserFactory
from organizacoes.factories import OrganizacaoFactory
from feed.forms import PostForm
from feed.models import Post


class PostFormTest(TestCase):
    def setUp(self) -> None:
        org = OrganizacaoFactory()
        self.user = UserFactory(organizacao=org)

    @override_settings(CELERY_TASK_ALWAYS_EAGER=True)
    @patch("feed.services._upload_media", return_value="ok")
    @patch("feed.tasks.upload_media.apply_async")
    def test_upload_uses_direct_service_when_eager(self, mock_apply, mock_upload):
        video = SimpleUploadedFile("v.mp4", b"00", content_type="video/mp4")
        form = PostForm(
            data={"tipo_feed": "global", "organizacao": str(self.user.organizacao.id)},
            files={"video": video},
            user=self.user,
        )
        self.assertTrue(form.is_valid())
        mock_upload.assert_called_once()
        mock_apply.assert_not_called()

    @patch("feed.services.shutil.which", return_value=None)
    def test_form_video_valid_without_preview(self, mock_which):
        video = SimpleUploadedFile("v.mp4", b"00", content_type="video/mp4")
        form = PostForm(
            data={"tipo_feed": "global", "organizacao": str(self.user.organizacao.id)},
            files={"video": video},
            user=self.user,
        )
        self.assertTrue(form.is_valid())
        self.assertIsNone(form._video_preview_key)
        self.assertIsInstance(form.cleaned_data["video"], str)

    def test_form_text_only_valid(self):
        form = PostForm(
            data={
                "tipo_feed": "global",
                "organizacao": str(self.user.organizacao.id),
                "conteudo": "Olá",
            },
            user=self.user,
        )
        self.assertTrue(form.is_valid())

    def test_form_no_content_no_media_invalid(self):
        form = PostForm(
            data={"tipo_feed": "global", "organizacao": str(self.user.organizacao.id)},
            user=self.user,
        )
        self.assertFalse(form.is_valid())
        self.assertIn("__all__", form.errors)

    @override_settings(FEED_IMAGE_MAX_SIZE=1)
    def test_form_image_too_large(self):
        img_io = io.BytesIO()
        Image.new("RGB", (1, 1)).save(img_io, format="PNG")
        image = SimpleUploadedFile("big.png", img_io.getvalue(), content_type="image/png")
        form = PostForm(
            data={"tipo_feed": "global", "organizacao": str(self.user.organizacao.id)},
            files={"image": image},
            user=self.user,
        )
        self.assertFalse(form.is_valid())
        self.assertIn("image", form.errors)

    @override_settings(CELERY_TASK_ALWAYS_EAGER=False)
    @patch("feed.tasks.POSTS_CREATED.inc")
    @patch("feed.tasks.notify_new_post.delay")
    def test_form_valid_triggers_metric_and_task(self, mock_notify, mock_inc):
        self.client.force_login(self.user)
        data = {
            "tipo_feed": "global",
            "conteudo": "Olá",
            "organizacao": str(self.user.organizacao.id),
        }
        resp = self.client.post(reverse("feed:nova_postagem"), data)
        self.assertEqual(resp.status_code, 302)
        post_id = str(Post.objects.latest("created_at").id)
        mock_inc.assert_called_once_with()
        mock_notify.assert_called_once_with(post_id)
