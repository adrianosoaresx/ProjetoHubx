from django.test import TestCase
from rest_framework.test import APIClient

from accounts.factories import UserFactory
from feed.factories import PostFactory
from feed.models import Bookmark
from organizacoes.factories import OrganizacaoFactory


class BookmarkAPITest(TestCase):
    def setUp(self) -> None:
        org = OrganizacaoFactory()
        self.user = UserFactory(organizacao=org)
        self.user.set_password("pass123")
        self.user.save()
        self.client = APIClient()
        self.client.force_authenticate(self.user)
        self.org = org

    def test_toggle_bookmark(self):
        post = PostFactory(autor=self.user, organizacao=self.org)
        url = f"/api/feed/posts/{post.id}/bookmark/"
        res = self.client.post(url)
        self.assertEqual(res.status_code, 201)
        self.assertTrue(res.data["bookmarked"])
        self.assertTrue(Bookmark.objects.filter(user=self.user, post=post).exists())

        res = self.client.post(url)
        self.assertEqual(res.status_code, 200)
        self.assertFalse(res.data["bookmarked"])
        self.assertFalse(Bookmark.objects.filter(user=self.user, post=post).exists())

    def test_list_bookmarks(self):
        post = PostFactory(autor=self.user, organizacao=self.org)
        Bookmark.objects.create(user=self.user, post=post)
        res = self.client.get("/api/feed/bookmarks/")
        self.assertEqual(res.status_code, 200)
        ids = [item["post"]["id"] for item in res.data]
        self.assertIn(str(post.id), ids)
