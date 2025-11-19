import sys
from types import SimpleNamespace
from unittest.mock import Mock, patch

from django.test import TestCase, override_settings

from accounts.factories import UserFactory
from accounts.models import UserType
from feed.models import Post
from organizacoes.factories import OrganizacaoFactory

if "feedparser" not in sys.modules:
    sys.modules["feedparser"] = Mock(parse=Mock(), mktime_tz=Mock())

from organizacoes.services.news_feed_publisher import publicar_feed_noticias


@override_settings(CELERY_TASK_ALWAYS_EAGER=True)
class PublicarFeedNoticiasTests(TestCase):
    @patch("organizacoes.services.news_feed_publisher._maybe_download_image", return_value=None)
    @patch("organizacoes.services.news_feed_publisher.notify_new_post")
    @patch("organizacoes.services.news_feed_publisher.feedparser.parse")
    @patch("feed.services.link_preview.requests.get")
    def test_publish_creates_posts_and_deduplicates(
        self,
        mock_get,
        mock_parse,
        mock_notify,
        mock_maybe_download,
    ):
        organizacao = OrganizacaoFactory(feed_noticias="https://example.com/rss")
        author = UserFactory(organizacao=organizacao, user_type=UserType.ADMIN.value)

        entries = [
            SimpleNamespace(
                id="guid-1",
                link="https://example.com/article-1",
                title="First post",
                summary="<p>Summary 1</p>",
                published="Mon, 01 Jan 2024 00:00:00 GMT",
            ),
            SimpleNamespace(
                id="guid-2",
                link="https://example.com/article-2",
                title="Second post",
                summary="<p>Summary 2</p>",
                published="Tue, 02 Jan 2024 00:00:00 GMT",
            ),
        ]
        mock_parse.return_value = SimpleNamespace(entries=entries)

        html_by_url = {
            "https://example.com/article-1": """
                <html>
                  <head>
                    <meta property=\"og:title\" content=\"First post\" />
                    <meta property=\"og:description\" content=\"Summary 1\" />
                    <meta property=\"og:site_name\" content=\"Example\" />
                  </head>
                </html>
            """,
            "https://example.com/article-2": """
                <html>
                  <head>
                    <meta property=\"og:title\" content=\"Second post\" />
                    <meta property=\"og:description\" content=\"Summary 2\" />
                    <meta property=\"og:image\" content=\"/image.png\" />
                  </head>
                </html>
            """,
        }

        def mock_request(url, *args, **kwargs):  # noqa: ANN001
            html = html_by_url.get(url)
            if html is None:
                raise AssertionError(f"Unexpected URL requested: {url}")
            response = Mock(status_code=200, text=html)
            response.raise_for_status = Mock()
            response.headers = {"Content-Type": "text/html"}
            return response

        mock_get.side_effect = mock_request

        created_posts = publicar_feed_noticias(max_items=5, tipo_feed="global")

        self.assertEqual(len(created_posts), 2)
        self.assertEqual(Post.objects.count(), 2)
        self.assertTrue(all(post.autor == author for post in created_posts))
        self.assertTrue(all(post.organizacao == organizacao for post in created_posts))
        self.assertTrue(all(post.link_preview["url"].startswith("https://example.com/article") for post in created_posts))
        self.assertEqual(mock_notify.call_count, 2)

        again_posts = publicar_feed_noticias(max_items=5, tipo_feed="global")

        self.assertEqual(again_posts, [])
        self.assertEqual(Post.objects.count(), 2)
        self.assertEqual(mock_notify.call_count, 2)
        mock_maybe_download.assert_called()
