from __future__ import annotations

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from PIL import Image
import io

from accounts.factories import UserFactory
from organizacoes.factories import OrganizacaoFactory
from feed.forms import PostForm


class PostFormTest(TestCase):
    def setUp(self) -> None:
        org = OrganizacaoFactory()
        self.user = UserFactory(organizacao=org)

    def test_form_video_valid(self):
        video = SimpleUploadedFile("v.mp4", b"00", content_type="video/mp4")
        form = PostForm(
            data={"tipo_feed": "global"}, files={"video": video}, user=self.user
        )
        self.assertTrue(form.is_valid())

    def test_form_text_only_valid(self):
        form = PostForm(
            data={"tipo_feed": "global", "conteudo": "Olá"},
            user=self.user,
        )
        self.assertTrue(form.is_valid())

    def test_form_no_content_no_media_invalid(self):
        form = PostForm(data={"tipo_feed": "global"}, user=self.user)
        self.assertFalse(form.is_valid())
        self.assertIn("__all__", form.errors)

    @override_settings(FEED_IMAGE_MAX_SIZE=1)
    def test_form_image_too_large(self):
        img_io = io.BytesIO()
        Image.new("RGB", (1, 1)).save(img_io, format="PNG")
        image = SimpleUploadedFile("big.png", img_io.getvalue(), content_type="image/png")
        form = PostForm(
            data={"tipo_feed": "global"}, files={"image": image}, user=self.user
        )
        self.assertFalse(form.is_valid())
        self.assertIn("image", form.errors)
