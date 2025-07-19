from django.test import TestCase
from django.contrib.contenttypes.models import ContentType

from accounts.models import User
from discussao.models import (
    CategoriaDiscussao,
    TopicoDiscussao,
    RespostaDiscussao,
    InteracaoDiscussao,
)


class DiscussaoModelTests(TestCase):
    def setUp(self):
        from organizacoes.models import Organizacao

        self.org = Organizacao.objects.create(nome="Org", cnpj="00.000.000/0001-99", slug="org")
        self.user = User.objects.create_user(
            username="u",
            email="u@example.com",
            password="pass",
            organizacao=self.org,
        )
        self.categoria = CategoriaDiscussao.objects.create(nome="Geral", organizacao=self.org)

    def test_unique_categoria(self):
        with self.assertRaises(Exception):
            CategoriaDiscussao.objects.create(nome="Geral", organizacao=self.org)

    def test_topico_slug_increment(self):
        topico = TopicoDiscussao.objects.create(
            categoria=self.categoria,
            titulo="Primeiro Topico",
            conteudo="oi",
            autor=self.user,
            publico_alvo=0,
        )
        slug = topico.slug
        topico.incrementar_visualizacao()
        topico.refresh_from_db()
        self.assertEqual(topico.numero_visualizacoes, 1)
        self.assertEqual(slug, topico.slug)

    def test_resposta_edit(self):
        topico = TopicoDiscussao.objects.create(
            categoria=self.categoria,
            titulo="T",
            conteudo="c",
            autor=self.user,
            publico_alvo=0,
        )
        resp = RespostaDiscussao.objects.create(topico=topico, autor=self.user, conteudo="olá")
        resp.editar_resposta("novo")
        resp.refresh_from_db()
        self.assertTrue(resp.editado)
        self.assertEqual(resp.conteudo, "novo")

    def test_interacao_unique(self):
        topico = TopicoDiscussao.objects.create(
            categoria=self.categoria,
            titulo="T2",
            conteudo="c",
            autor=self.user,
            publico_alvo=0,
        )
        ct = ContentType.objects.get_for_model(topico)
        InteracaoDiscussao.objects.create(user=self.user, content_type=ct, object_id=topico.id, tipo="like")
        with self.assertRaises(Exception):
            InteracaoDiscussao.objects.create(user=self.user, content_type=ct, object_id=topico.id, tipo="like")
