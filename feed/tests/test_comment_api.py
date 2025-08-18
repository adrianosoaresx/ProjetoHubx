from django.test import TestCase
from rest_framework.test import APIClient

from accounts.factories import UserFactory
from feed.factories import PostFactory
from feed.models import Comment
from organizacoes.factories import OrganizacaoFactory


class CommentPermissionAPITest(TestCase):
    def setUp(self) -> None:
        self.org = OrganizacaoFactory()
        self.author = UserFactory(organizacao=self.org)
        self.author.set_password("pass123")
        self.author.save()
        self.moderator = UserFactory(organizacao=self.org, is_staff=True)
        self.moderator.set_password("pass123")
        self.moderator.save()
        self.other = UserFactory(organizacao=self.org)
        self.other.set_password("pass123")
        self.other.save()
        self.post = PostFactory(autor=self.author, organizacao=self.org)
        self.comment = Comment.objects.create(post=self.post, user=self.author, texto="orig")
        self.client = APIClient()

    def test_author_can_update_comment(self):
        self.client.force_authenticate(self.author)
        res = self.client.patch(
            f"/api/feed/comments/{self.comment.id}/", {"texto": "edit"}, format="json"
        )
        self.assertEqual(res.status_code, 200)
        self.comment.refresh_from_db()
        self.assertEqual(self.comment.texto, "edit")

    def test_moderator_can_update_comment(self):
        self.client.force_authenticate(self.moderator)
        res = self.client.patch(
            f"/api/feed/comments/{self.comment.id}/", {"texto": "mod"}, format="json"
        )
        self.assertEqual(res.status_code, 200)
        self.comment.refresh_from_db()
        self.assertEqual(self.comment.texto, "mod")

    def test_other_user_cannot_update_comment(self):
        self.client.force_authenticate(self.other)
        res = self.client.patch(
            f"/api/feed/comments/{self.comment.id}/", {"texto": "fail"}, format="json"
        )
        self.assertEqual(res.status_code, 403)

    def test_other_user_cannot_delete_comment(self):
        self.client.force_authenticate(self.other)
        res = self.client.delete(f"/api/feed/comments/{self.comment.id}/")
        self.assertEqual(res.status_code, 403)
