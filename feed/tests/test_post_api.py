from __future__ import annotations

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from PIL import Image
import io
import subprocess
import tempfile
from rest_framework.test import APIClient

from accounts.factories import UserFactory
from organizacoes.factories import OrganizacaoFactory


class PostAPITest(TestCase):
    def setUp(self) -> None:
        org = OrganizacaoFactory()
        self.user = UserFactory(organizacao=org)
        self.user.set_password("pass123")
        self.user.save()
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def test_create_text_post(self):
        res = self.client.post(
            "/api/feed/posts/", {"conteudo": "ola", "tipo_feed": "global"}
        )
        self.assertEqual(res.status_code, 201)
        self.assertEqual(res.data["conteudo"], "ola")

    def test_create_image_post(self):
        img_io = io.BytesIO()
        Image.new("RGB", (1, 1)).save(img_io, format="PNG")
        image = SimpleUploadedFile("t.png", img_io.getvalue(), content_type="image/png")
        res = self.client.post(
            "/api/feed/posts/", {"tipo_feed": "global", "image": image}, format="multipart"
        )
        self.assertEqual(res.status_code, 201)
        self.assertTrue(res.data["image"])  # caminho salvo

    def test_create_pdf_post(self):
        pdf = SimpleUploadedFile(
            "f.pdf", b"%PDF-1.4", content_type="application/pdf"
        )
        res = self.client.post(
            "/api/feed/posts/", {"tipo_feed": "global", "pdf": pdf}, format="multipart"
        )
        self.assertEqual(res.status_code, 201)

    def test_create_video_post(self):
        tmp = tempfile.NamedTemporaryFile(suffix=".mp4")
        subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-f",
                "lavfi",
                "-i",
                "color=c=black:s=16x16:d=1",
                "-pix_fmt",
                "yuv420p",
                tmp.name,
            ],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        tmp.seek(0)
        video = SimpleUploadedFile("v.mp4", tmp.read(), content_type="video/mp4")
        res = self.client.post(
            "/api/feed/posts/", {"tipo_feed": "global", "video": video}, format="multipart"
        )
        self.assertEqual(res.status_code, 201)
        self.assertTrue(res.data["video_preview"])
        self.assertTrue(res.data["video_preview_url"])

    def test_conteudo_limit(self):
        res = self.client.post(
            "/api/feed/posts/", {"conteudo": "a" * 501, "tipo_feed": "global"}
        )
        self.assertEqual(res.status_code, 400)

    @override_settings(FEED_IMAGE_MAX_SIZE=1)
    def test_upload_exceeds_limit(self):
        img_io = io.BytesIO()
        Image.new("RGB", (1, 1)).save(img_io, format="PNG")
        image = SimpleUploadedFile("big.png", img_io.getvalue(), content_type="image/png")
        res = self.client.post(
            "/api/feed/posts/", {"tipo_feed": "global", "image": image}, format="multipart"
        )
        self.assertEqual(res.status_code, 400)

    def test_soft_delete(self):
        res = self.client.post(
            "/api/feed/posts/", {"conteudo": "oi", "tipo_feed": "global"}
        )
        post_id = res.data["id"]
        del_res = self.client.delete(f"/api/feed/posts/{post_id}/")
        self.assertEqual(del_res.status_code, 204)
        list_res = self.client.get("/api/feed/posts/")
        data = list_res.data["results"] if isinstance(list_res.data, dict) else list_res.data
        ids = [item["id"] for item in data]
        self.assertNotIn(post_id, ids)

    def test_update_not_author_forbidden(self):
        res = self.client.post(
            "/api/feed/posts/", {"conteudo": "oi", "tipo_feed": "global"}
        )
        post_id = res.data["id"]
        other_user = UserFactory(organizacao=self.user.organizacao)
        self.client.force_authenticate(other_user)
        res = self.client.patch(
            f"/api/feed/posts/{post_id}/", {"conteudo": "novo"}
        )
        self.assertEqual(res.status_code, 403)
