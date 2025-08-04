from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from accounts.models import UserType
from feed.models import Post
from nucleos.models import Nucleo
from organizacoes.models import Organizacao


class FeedPublicPrivateTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.root_user = User.objects.create_superuser(
            email="root@example.com",
            username="root",
            password="pass",
            organizacao=None,
        )
        self.user = User.objects.create_user(
            email="normal@example.com",
            username="normal",
            password="pass",
            user_type=UserType.NUCLEADO,
            organizacao=None,
        )

        self.org = Organizacao.objects.create(nome="Org", cnpj="00.000.000/0001-00")
        # associar usuários à organização para que apareçam no feed
        self.user.organizacao = self.org
        self.user.save()
        self.nucleo = Nucleo.objects.create(nome="N1", slug="n1", organizacao=self.org)
        self.nucleo.participacoes.create(user=self.user)
        self.client.force_login(self.user)

    def test_global_post_appears_on_feed(self):
        post = Post.objects.create(
            autor=self.user,
            conteudo="global",
            tipo_feed="global",
            organizacao=self.org,
        )
        post.moderacao.status = "aprovado"
        post.moderacao.save()
        resp = self.client.get(reverse("feed:listar"))
        self.assertIn("global", resp.content.decode())

    def test_nucleo_post_hidden_on_feed(self):
        post = Post.objects.create(
            autor=self.user,
            conteudo="nucleo",
            tipo_feed="nucleo",
            organizacao=self.org,
        )
        post.moderacao.status = "aprovado"
        post.moderacao.save()
        resp = self.client.get(reverse("feed:listar"))
        self.assertEqual(len(resp.context.get("posts", [])), 0)

    def test_nucleo_post_only_with_filter(self):
        post = Post.objects.create(
            autor=self.user,
            conteudo="nucleo",
            nucleo=self.nucleo,
            tipo_feed="nucleo",
            organizacao=self.org,
        )
        post.moderacao.status = "aprovado"
        post.moderacao.save()
        resp = self.client.get(reverse("feed:listar"))
        self.assertEqual(len(resp.context.get("posts", [])), 0)

        resp = self.client.get(
            reverse("feed:listar") + f"?tipo_feed=nucleo&nucleo={self.nucleo.id}"
        )
        posts = resp.context.get("posts", [])
        self.assertEqual(len(posts), 1)
        self.assertEqual(posts[0].nucleo, self.nucleo)

    def test_search_returns_matching_posts(self):
        p1 = Post.objects.create(autor=self.user, conteudo="alpha bravo", organizacao=self.org)
        p2 = Post.objects.create(autor=self.user, conteudo="charlie delta", organizacao=self.org)
        p1.moderacao.status = p2.moderacao.status = "aprovado"
        p1.moderacao.save()
        p2.moderacao.save()
        resp = self.client.get(reverse("feed:listar") + "?q=alpha")
        self.assertEqual(len(resp.context.get("posts", [])), 1)
        self.assertIn("alpha bravo", resp.content.decode())
