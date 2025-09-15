from django.test import TestCase, override_settings
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
        self.assertEqual(Bookmark.all_objects.filter(user=self.user, post=post).count(), 1)

        res = self.client.post(url)
        self.assertEqual(res.status_code, 200)
        self.assertFalse(res.data["bookmarked"])
        self.assertFalse(Bookmark.objects.filter(user=self.user, post=post).exists())
        self.assertEqual(Bookmark.all_objects.filter(user=self.user, post=post).count(), 1)
        bookmark = Bookmark.all_objects.get(user=self.user, post=post)
        self.assertTrue(bookmark.deleted)

        res = self.client.post(url)
        self.assertEqual(res.status_code, 201)
        self.assertTrue(res.data["bookmarked"])
        self.assertTrue(Bookmark.objects.filter(user=self.user, post=post).exists())
        self.assertEqual(Bookmark.all_objects.filter(user=self.user, post=post).count(), 1)

        res = self.client.post(url)
        self.assertEqual(res.status_code, 200)
        self.assertFalse(res.data["bookmarked"])
        self.assertFalse(Bookmark.objects.filter(user=self.user, post=post).exists())
        self.assertEqual(Bookmark.all_objects.filter(user=self.user, post=post).count(), 1)

    def test_list_bookmarks(self):
        post = PostFactory(autor=self.user, organizacao=self.org)
        Bookmark.objects.create(user=self.user, post=post)
        res = self.client.get("/api/feed/bookmarks/")
        self.assertEqual(res.status_code, 200)
        ids = [item["post"]["id"] for item in res.data]
        self.assertIn(str(post.id), ids)

    @override_settings(FEED_RATE_LIMIT_READ="1/m")
    def test_bookmark_rate_limit_exceeded(self):
        post = PostFactory(autor=self.user, organizacao=self.org)
        url = f"/api/feed/posts/{post.id}/bookmark/"
        res1 = self.client.post(url)
        self.assertEqual(res1.status_code, 201)
        res2 = self.client.post(url)
        self.assertEqual(res2.status_code, 429)
        self.assertTrue(Bookmark.objects.filter(user=self.user, post=post).exists())

    def test_duplicate_bookmarks_do_not_error(self):
        post = PostFactory(autor=self.user, organizacao=self.org)
        # create a soft-deleted bookmark first so it has a lower PK
        Bookmark.objects.create(user=self.user, post=post, deleted=True)
        Bookmark.objects.create(user=self.user, post=post)
        url = f"/api/feed/posts/{post.id}/bookmark/"

        res = self.client.post(url)
        self.assertEqual(res.status_code, 200)
        self.assertFalse(res.data["bookmarked"])
        self.assertEqual(Bookmark.objects.filter(user=self.user, post=post).count(), 0)
        self.assertEqual(
            Bookmark.all_objects.filter(user=self.user, post=post).count(),
            1,
        )

        res = self.client.post(url)
        self.assertEqual(res.status_code, 201)
        self.assertTrue(res.data["bookmarked"])
        self.assertEqual(Bookmark.objects.filter(user=self.user, post=post).count(), 1)
        self.assertEqual(
            Bookmark.all_objects.filter(user=self.user, post=post).count(),
            1,
        )
