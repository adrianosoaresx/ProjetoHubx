from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError

from accounts.models import UserType
from organizacoes.models import Organizacao
from nucleos.models import Nucleo

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
        tipo_client, _ = UserType.objects.get_or_create(descricao="client")
        self.user = User.objects.create_user("normal", password="pass", tipo=tipo_client)

        self.client = Client()

        org = Organizacao.objects.create(nome="Org", cnpj="00.000.000/0001-00")
        self.nucleo1 = Nucleo.objects.create(nome="N1", organizacao=org)
        self.nucleo2 = Nucleo.objects.create(nome="N2", organizacao=org)
        self.nucleo1.membros.add(self.user)

    def test_common_user_can_post(self):
        self.client.force_login(self.user)
        response = self.client.post(
            reverse("feed:nova_postagem"),
            {"conteudo": "hello", "tipo_feed": Post.PUBLICO},
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Post.objects.filter(conteudo="hello", autor=self.user).exists())

    def test_root_user_is_forbidden(self):
        self.client.force_login(self.root_user)
        response = self.client.post(
            reverse("feed:nova_postagem"),
            {"conteudo": "root post", "tipo_feed": Post.PUBLICO},
        )
        self.assertEqual(response.status_code, 403)

    def test_feed_nucleo_filter(self):
        Post.objects.create(autor=self.user, conteudo="A", tipo_feed=Post.NUCLEO, nucleo=self.nucleo1)
        Post.objects.create(autor=self.user, conteudo="B", tipo_feed=Post.NUCLEO, nucleo=self.nucleo2)

        self.client.force_login(self.user)
        url = reverse("feed:feed") + "?tipo=nucleo"
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        posts = list(response.context["posts"])
        self.assertEqual(len(posts), 1)
        self.assertEqual(posts[0].nucleo, self.nucleo1)

