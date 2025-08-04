from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase

from feed.models import Post
from organizacoes.models import Organizacao


class VideoUploadTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(
            email="user@example.com",
            username="user",
            password="pass",
            organizacao=None,
        )
        self.org = Organizacao.objects.create(nome="Org", cnpj="00.000.000/0001-00")
        self.user.organizacao = self.org
        self.user.save()

    def test_upload_video_valid(self):
        file = SimpleUploadedFile("movie.mp4", b"data", content_type="video/mp4")
        post = Post.objects.create(autor=self.user, organizacao=self.org, video=file)
        self.assertTrue(post.video.name.startswith("videos/"))

    def test_upload_invalid_extension(self):
        file = SimpleUploadedFile("movie.avi", b"data", content_type="video/avi")
        post = Post(autor=self.user, organizacao=self.org, video=file)
        with self.assertRaises(ValidationError):
            post.full_clean()
