from __future__ import annotations

from django.test import TestCase, override_settings
from unittest.mock import patch
import builtins

from feed.api import PostSerializer


class PresignedURLTest(TestCase):
    @override_settings(AWS_STORAGE_BUCKET_NAME="bucket")
    def test_fallback_without_boto3(self):
        original_import = builtins.__import__

        def fake_import(name, *args, **kwargs):
            if name == "boto3":
                raise ImportError()
            return original_import(name, *args, **kwargs)

        with (
            patch("feed.api.default_storage.url", return_value="fallback") as mock_url,
            patch("builtins.__import__", side_effect=fake_import),
        ):
            serializer = PostSerializer()
            result = serializer._generate_presigned("file")
        self.assertEqual(result, "fallback")
        mock_url.assert_called_once_with("file")
