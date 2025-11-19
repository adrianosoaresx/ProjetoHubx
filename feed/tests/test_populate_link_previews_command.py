from __future__ import annotations

from django.core.management import call_command
from django.test import TestCase
from unittest.mock import patch

from accounts.factories import UserFactory
from feed.factories import PostFactory
from organizacoes.factories import OrganizacaoFactory
from feed.services.link_preview import LinkPreviewData


class PopulatePostLinkPreviewsCommandTest(TestCase):
    @patch("feed.management.commands.populate_post_link_previews.extract_link_preview")
    def test_populates_missing_preview(self, mock_extract):
        organizacao = OrganizacaoFactory()
        autor = UserFactory(organizacao=organizacao)
        post = PostFactory(conteudo="Veja https://example.com/42", organizacao=organizacao, autor=autor)
        mock_extract.return_value = LinkPreviewData(
            url="https://example.com/42",
            title="Example",
            description="Desc",
            image="https://example.com/img.jpg",
            site_name="Example",
        )

        call_command("populate_post_link_previews", limit=10)

        post.refresh_from_db()
        self.assertEqual(post.link_preview["url"], "https://example.com/42")
        self.assertEqual(post.link_preview["title"], "Example")
        mock_extract.assert_called_once_with("https://example.com/42")

    @patch("feed.management.commands.populate_post_link_previews.extract_link_preview")
    def test_dry_run_does_not_persist(self, mock_extract):
        organizacao = OrganizacaoFactory()
        autor = UserFactory(organizacao=organizacao)
        post = PostFactory(conteudo="https://example.com/55", organizacao=organizacao, autor=autor)
        mock_extract.return_value = LinkPreviewData(
            url="https://example.com/55",
            title="Title",
            description="",
            image=None,
            site_name="Example",
        )

        call_command("populate_post_link_previews", dry_run=True, limit=1)

        post.refresh_from_db()
        self.assertEqual(post.link_preview, {})
        mock_extract.assert_called_once()
