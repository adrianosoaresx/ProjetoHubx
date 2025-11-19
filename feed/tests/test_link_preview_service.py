from __future__ import annotations

from unittest.mock import Mock, patch

import requests
from django.test import SimpleTestCase

from feed.services.link_preview import (
    InvalidLinkPreviewURLError,
    LinkPreviewRequestError,
    MissingLinkPreviewURLError,
    extract_link_preview,
)


class ExtractLinkPreviewTest(SimpleTestCase):
    def test_missing_url_raises_error(self):
        with self.assertRaises(MissingLinkPreviewURLError):
            extract_link_preview("")

    def test_invalid_scheme_raises_error(self):
        with self.assertRaises(InvalidLinkPreviewURLError):
            extract_link_preview("ftp://example.com")

    @patch("feed.services.link_preview.requests.get")
    def test_successful_response_parses_metadata(self, mock_get):
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

        preview = extract_link_preview("https://example.com/post")

        self.assertEqual(preview.url, "https://example.com/post")
        self.assertEqual(preview.title, "Example Title")
        self.assertEqual(preview.description, "Example description")
        self.assertEqual(preview.image, "https://example.com/image.jpg")
        self.assertEqual(preview.site_name, "Example Site")

    @patch("feed.services.link_preview.requests.get", side_effect=requests.RequestException)
    def test_request_errors_are_wrapped(self, mock_get):  # noqa: ARG002
        with self.assertRaises(LinkPreviewRequestError):
            extract_link_preview("https://example.com/post")

    @patch("feed.services.link_preview.requests.get")
    def test_missing_meta_tags_use_title_and_hostname(self, mock_get):
        html = """
        <html>
          <head>
            <title>Fallback Title</title>
          </head>
          <body>
            <p>Content without meta tags.</p>
          </body>
        </html>
        """
        mock_response = Mock(status_code=200, text=html)
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        preview = extract_link_preview("https://example.org/article")

        self.assertEqual(preview.title, "Fallback Title")
        self.assertEqual(preview.description, "")
        self.assertIsNone(preview.image)
        self.assertEqual(preview.site_name, "example.org")

    @patch("feed.services.link_preview.requests.get")
    def test_empty_title_uses_url_when_no_metadata(self, mock_get):
        html = """
        <html>
          <head></head>
          <body>
            <p>Page without title or meta.</p>
          </body>
        </html>
        """
        mock_response = Mock(status_code=200, text=html)
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        preview = extract_link_preview("https://example.net/path")

        self.assertEqual(preview.title, "https://example.net/path")
        self.assertEqual(preview.description, "")
        self.assertIsNone(preview.image)
        self.assertEqual(preview.site_name, "example.net")
