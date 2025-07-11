from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model

from accounts.models import UserType
from organizacoes.models import Organizacao
from nucleos.models import Nucleo
from feed.models import Post


class FeedPublicPrivateTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.root_user = User.objects.get(username="root")
        tipo_client, _ = UserType.objects.get_or_create(descricao="client")
        self.user = User.objects.create_user("normal", password="pass", tipo=tipo_client)

        org = Organizacao.objects.create(nome="Org", cnpj="00.000.000/0001-00")
        self.nucleo = Nucleo.objects.create(nome="N1", organizacao=org)
        self.nucleo.membros.add(self.user)
        self.client.force_login(self.user)

    def test_public_post_appears_on_feed(self):
        Post.objects.create(
            autor=self.user,
            conteudo="public",
            publico=True,
            tipo_feed=Post.PUBLICO,
        )
        resp = self.client.get(reverse("feed:listar"))
        self.assertContains(resp, "public")

    def test_private_post_hidden_on_feed(self):
        Post.objects.create(
            autor=self.user,
            conteudo="private",
            publico=False,
            tipo_feed=Post.PUBLICO,
        )
        resp = self.client.get(reverse("feed:listar"))
        self.assertNotContains(resp, "private")

    def test_nucleo_post_only_with_filter(self):
        Post.objects.create(
            autor=self.user,
            conteudo="nucleo",
            nucleo=self.nucleo,
            publico=False,
            tipo_feed=Post.NUCLEO,
        )
        resp = self.client.get(reverse("feed:listar"))
        self.assertEqual(len(resp.context["posts"]), 0)

        resp = self.client.get(reverse("feed:listar") + f"?nucleo={self.nucleo.id}")
        self.assertEqual(len(resp.context["posts"]), 1)
        self.assertEqual(resp.context["posts"][0].nucleo, self.nucleo)

    def test_search_returns_matching_posts(self):
        Post.objects.create(autor=self.user, conteudo="alpha bravo")
        Post.objects.create(autor=self.user, conteudo="charlie delta")
        resp = self.client.get(reverse("feed:listar") + "?q=alpha")
        self.assertEqual(len(resp.context["posts"]), 1)
        self.assertContains(resp, "alpha bravo")
