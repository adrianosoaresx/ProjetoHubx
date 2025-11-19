from __future__ import annotations

from unittest.mock import Mock, patch

import requests
from django.test import TestCase
from rest_framework.test import APIClient

from accounts.factories import UserFactory
from organizacoes.factories import OrganizacaoFactory


class LinkPreviewApiTest(TestCase):
    def setUp(self) -> None:
        organizacao = OrganizacaoFactory()
        self.user = UserFactory(organizacao=organizacao)
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def test_missing_url_returns_error(self):
        res = self.client.get("/api/feed/posts/link-preview/")
        self.assertEqual(res.status_code, 400)

    def test_invalid_url_returns_error(self):
        res = self.client.get("/api/feed/posts/link-preview/", {"url": "ftp://example.com"})
        self.assertEqual(res.status_code, 400)

    @patch("feed.services.link_preview.requests.get")
    def test_extracts_basic_metadata(self, mock_get):
        html = """
        <html>
          <head>
            <title>Example Title</title>
            <meta property="og:description" content="Example description" />
            <meta property="og:image" content="/image.jpg" />
            <meta property="og:site_name" content="Example Site" />
          </head>
        </html>
        """
        mock_response = Mock(status_code=200, text=html)
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        res = self.client.get(
            "/api/feed/posts/link-preview/",
            {"url": "https://example.com/post"},
        )

        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data["url"], "https://example.com/post")
        self.assertEqual(res.data["title"], "Example Title")
        self.assertEqual(res.data["description"], "Example description")
        self.assertEqual(res.data["image"], "https://example.com/image.jpg")
        self.assertEqual(res.data["site_name"], "Example Site")

    @patch("feed.services.link_preview.requests.get", side_effect=requests.RequestException)
    def test_handles_request_errors(self, mock_get):  # noqa: ARG002
        res = self.client.get("/api/feed/posts/link-preview/", {"url": "https://example.com"})
        self.assertEqual(res.status_code, 400)
