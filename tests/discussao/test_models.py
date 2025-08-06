import pytest
from django.contrib.contenttypes.models import ContentType
from django.db import IntegrityError
from django.utils.text import slugify

from discussao.models import (
    CategoriaDiscussao,
    InteracaoDiscussao,
    RespostaDiscussao,
    Tag,
    TopicoDiscussao,
)

pytestmark = pytest.mark.django_db


@pytest.fixture
def categoria(organizacao):
    return CategoriaDiscussao.objects.create(nome="Geral", organizacao=organizacao)


@pytest.fixture
def topico(categoria, admin_user):
    return TopicoDiscussao.objects.create(
        categoria=categoria,
        titulo="Titulo Topico",
        conteudo="Conteudo",
        autor=admin_user,
        publico_alvo=0,
    )


def test_categoria_slug_unique_and_autocreated(categoria, organizacao):
    assert categoria.slug == slugify(categoria.nome)
    with pytest.raises(IntegrityError):
        CategoriaDiscussao.objects.create(
            nome="Geral",
            organizacao=organizacao,
        )


def test_topico_slug_and_visualizacao(topico):
    assert topico.slug == slugify(topico.titulo)
    assert topico.numero_visualizacoes == 0
    topico.incrementar_visualizacao()
    topico.refresh_from_db()
    assert topico.numero_visualizacoes == 1


def test_resposta_editar_e_reply(topico, admin_user):
    resp = RespostaDiscussao.objects.create(topico=topico, autor=admin_user, conteudo="olá")
    filho = RespostaDiscussao.objects.create(topico=topico, autor=admin_user, conteudo="filho", reply_to=resp)
    resp.editar_resposta("novo")
    resp.refresh_from_db()
    assert resp.editado is True
    assert resp.conteudo == "novo"
    assert filho in resp.respostas_filhas.all()


def test_timestamp_and_softdelete(topico):
    assert topico.created is not None
    assert topico.modified is not None
    topico.delete()
    assert not TopicoDiscussao.objects.filter(pk=topico.pk).exists()
    assert TopicoDiscussao.all_objects.filter(pk=topico.pk).exists()


def test_tag_soft_delete():
    tag = Tag.objects.create(nome="python")
    tag.delete()
    assert not Tag.objects.filter(pk=tag.pk).exists()
    assert Tag.all_objects.filter(pk=tag.pk).exists()


def test_interacao_unique_and_toggle(topico, admin_user):
    ct = ContentType.objects.get_for_model(topico)
    like, created = InteracaoDiscussao.objects.get_or_create(
        user=admin_user, content_type=ct, object_id=topico.id, defaults={"tipo": "like"}
    )
    assert created
    assert InteracaoDiscussao.objects.count() == 1
    like2, created2 = InteracaoDiscussao.objects.get_or_create(
        user=admin_user, content_type=ct, object_id=topico.id, defaults={"tipo": "dislike"}
    )
    assert not created2
    like2.tipo = "dislike"
    like2.save()
    assert InteracaoDiscussao.objects.count() == 1
    assert InteracaoDiscussao.objects.get().tipo == "dislike"
    with pytest.raises(IntegrityError):
        InteracaoDiscussao.objects.create(user=admin_user, content_type=ct, object_id=topico.id, tipo="like")
