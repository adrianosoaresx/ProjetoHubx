from __future__ import annotations

from datetime import timedelta

from django.test import RequestFactory, TestCase
from django.utils import timezone

from accounts.factories import UserFactory
from feed.factories import PostFactory
from feed.views import FeedListView
from organizacoes.factories import OrganizacaoFactory


class FeedFilterViewTest(TestCase):
    def setUp(self) -> None:
        org = OrganizacaoFactory()
        self.user = UserFactory(organizacao=org)
        self.client.force_login(self.user)

    def test_date_range_filters(self) -> None:
        older = PostFactory(autor=self.user, created_at=timezone.now() - timedelta(days=5))
        newer = PostFactory(autor=self.user, created_at=timezone.now() - timedelta(days=1))
        rf = RequestFactory()
        date_from = (timezone.now() - timedelta(days=2)).date().isoformat()
        request = rf.get("/feed/", {"date_from": date_from})
        request.user = self.user
        view = FeedListView()
        view.request = request
        qs = view.get_queryset()
        self.assertIn(newer, qs)
        self.assertNotIn(older, qs)
