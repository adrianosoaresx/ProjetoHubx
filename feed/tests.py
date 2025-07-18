from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import Client, TestCase
from django.urls import reverse

from accounts.enums import TipoUsuario
from nucleos.models import Nucleo
from organizacoes.models import Organizacao

from .models import Post


class PostModelTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user("user", password="pass")

    def test_tipo_feed_validation(self):
        post = Post(autor=self.user, conteudo="ok", tipo_feed=Post.PUBLICO)
        post.full_clean()  # should not raise
        post.save()

        invalid = Post(autor=self.user, conteudo="bad", tipo_feed="privado")
        with self.assertRaises(ValidationError):
            invalid.full_clean()


class FeedViewTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.root_user = User.objects.get(username="root")
        self.user = User.objects.create_user(
            "normal", password="pass"
        )

        self.client = Client()

        org = Organizacao.objects.create(nome="Org", cnpj="00.000.000/0001-00")
        self.nucleo1 = Nucleo.objects.create(nome="N1", organizacao=org)
        self.nucleo2 = Nucleo.objects.create(nome="N2", organizacao=org)
        self.nucleo1.membros.add(self.user)

    def test_button_visibility(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse("feed:listar"))
        self.assertContains(response, "Nova postagem")

        self.client.force_login(self.root_user)
        response = self.client.get(reverse("feed:listar"))
        self.assertNotContains(response, "Nova postagem")

    def test_common_user_can_post(self):
        self.client.force_login(self.user)
        response = self.client.post(
            reverse("feed:nova_postagem"),
            {"conteudo": "hello", "destino": "publico"},
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Post.objects.filter(conteudo="hello", autor=self.user).exists())

    def test_root_user_is_forbidden(self):
        self.client.force_login(self.root_user)
        response = self.client.post(
            reverse("feed:nova_postagem"),
            {"conteudo": "root post", "destino": "publico"},
        )
        self.assertEqual(response.status_code, 403)

    def test_feed_nucleo_filter(self):
        Post.objects.create(
            autor=self.user, conteudo="A", tipo_feed=Post.NUCLEO, nucleo=self.nucleo1
        )
        Post.objects.create(
            autor=self.user, conteudo="B", tipo_feed=Post.NUCLEO, nucleo=self.nucleo2
        )

        self.client.force_login(self.user)
        url = reverse("feed:listar") + f"?nucleo={self.nucleo1.id}"
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        posts = list(response.context["posts"])
        self.assertEqual(len(posts), 1)
        self.assertEqual(posts[0].nucleo, self.nucleo1)

    def test_feed_search(self):
        Post.objects.create(autor=self.user, conteudo="foo bar")
        Post.objects.create(autor=self.user, conteudo="baz qux")

        self.client.force_login(self.user)
        url = reverse("feed:listar") + "?q=qux"
        response = self.client.get(url)
        self.assertEqual(len(response.context["posts"]), 1)
        self.assertContains(response, "baz qux")

    def test_form_has_submit_button(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse("feed:nova_postagem"))
        self.assertContains(response, 'type="submit"')

    def test_feed_without_nucleo_shows_public_only(self):
        Post.objects.create(autor=self.user, conteudo="public", publico=True)
        Post.objects.create(
            autor=self.user,
            conteudo="priv",
            publico=False,
            nucleo=self.nucleo1,
            tipo_feed=Post.NUCLEO,
        )
        self.client.force_login(self.user)
        resp = self.client.get(reverse("feed:listar"))
        self.assertEqual(len(resp.context["posts"]), 1)
        self.assertIsNone(resp.context["posts"][0].nucleo)
