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
        )
        self.user = User.objects.create_user(
            email="normal@example.com",
            username="normal",
            password="pass",
            user_type=UserType.NUCLEADO,
        )

        self.org = Organizacao.objects.create(nome="Org", cnpj="00.000.000/0001-00")
        self.nucleo = Nucleo.objects.create(nome="N1", organizacao=self.org)
        self.nucleo.participacoes.create(user=self.user)
        self.client.force_login(self.user)

    def test_global_post_appears_on_feed(self):
        Post.objects.create(
            autor=self.user,
            conteudo="global",
            tipo_feed="global",
            organizacao=self.org,
        )
        resp = self.client.get(reverse("feed:listar"))
        self.assertContains(resp, "global")

    def test_nucleo_post_hidden_on_feed(self):
        Post.objects.create(
            autor=self.user,
            conteudo="nucleo",
            tipo_feed="nucleo",
            organizacao=self.org,
        )
        resp = self.client.get(reverse("feed:listar"))
        self.assertNotContains(resp, "nucleo")

    def test_nucleo_post_only_with_filter(self):
        Post.objects.create(
            autor=self.user,
            conteudo="nucleo",
            nucleo=self.nucleo,
            tipo_feed="nucleo",
            organizacao=self.org,
        )
        resp = self.client.get(reverse("feed:listar"))
        self.assertEqual(len(resp.context["posts"]), 0)

        resp = self.client.get(reverse("feed:listar") + f"?nucleo={self.nucleo.id}")
        self.assertEqual(len(resp.context["posts"]), 1)
        self.assertEqual(resp.context["posts"][0].nucleo, self.nucleo)

    def test_search_returns_matching_posts(self):
        Post.objects.create(autor=self.user, conteudo="alpha bravo", organizacao=self.org)
        Post.objects.create(autor=self.user, conteudo="charlie delta", organizacao=self.org)
        resp = self.client.get(reverse("feed:listar") + "?q=alpha")
        self.assertEqual(len(resp.context["posts"]), 1)
        self.assertContains(resp, "alpha bravo")
