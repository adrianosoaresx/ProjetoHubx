from django.db import connection
from django.test import RequestFactory, TestCase, override_settings
from django.test.utils import CaptureQueriesContext

from accounts.factories import UserFactory
from feed.factories import PostFactory
from feed.models import Post, Reacao
from feed.views import FeedListView
from organizacoes.factories import OrganizacaoFactory


@override_settings(NOTIFICATIONS_ENABLED=False)
class FeedQueryCountTest(TestCase):
    def setUp(self) -> None:
        org = OrganizacaoFactory()
        self.user = UserFactory(organizacao=org)
        self.rf = RequestFactory()

    def _get_queryset(self):
        request = self.rf.get("/")
        request.user = self.user
        view = FeedListView()
        view.request = request
        return view.get_queryset()

    def test_feed_list_annotated_counts_reduce_queries(self) -> None:
        for _ in range(2):
            post = PostFactory(autor=self.user)
            Reacao.objects.create(post=post, user=self.user, vote="like")
            Reacao.objects.create(post=post, user=self.user, vote="share")

        with CaptureQueriesContext(connection) as ctx_annotated:
            list(self._get_queryset())
        annotated_queries = len(ctx_annotated)

        with CaptureQueriesContext(connection) as ctx_manual:
            posts = list(Post.objects.all())
            for post in posts:
                Reacao.objects.filter(post=post, vote="like").count()
                Reacao.objects.filter(post=post, vote="share").count()
        manual_queries = len(ctx_manual)

        self.assertLess(annotated_queries, manual_queries)

